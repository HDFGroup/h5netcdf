import netCDF4
import numpy as np
import sys

PY2 = sys.version_info[0] < 3

import h5netcdf
from h5netcdf import legacyapi
import h5py
import pytest

from pytest import fixture, raises


@pytest.fixture
def tmp_netcdf(tmpdir):
    return str(tmpdir.join('testfile.nc'))


def string_to_char(arr):
    """Like nc4.stringtochar, but faster and more flexible.
    """
    # ensure the array is contiguous
    arr = np.array(arr, copy=False, order='C')
    kind = arr.dtype.kind
    if kind not in ['U', 'S']:
        raise ValueError('argument must be a string')
    return arr.reshape(arr.shape + (1,)).view(kind + '1')


def array_equal(a, b):
    a, b = map(np.array, (a[...], b[...]))
    if a.shape != b.shape:
        return False
    try:
        return np.allclose(a, b)
    except TypeError:
        return (a == b).all()


_char_array = string_to_char(np.array(['a', 'b', 'c', 'foo', 'bar', 'baz'],
                                      dtype='S'))


def write_legacy_netcdf(tmp_netcdf, write_module):
    ds = write_module.Dataset(tmp_netcdf, 'w')
    ds.setncattr('global', 42)
    ds.other_attr = 'yes'
    ds.createDimension('x', 4)
    ds.createDimension('y', 5)
    ds.createDimension('z', 6)
    ds.createDimension('string3', 3)

    v = ds.createVariable('foo', float, ('x', 'y'))
    v[...] = 1
    v.setncattr('units', 'meters')

    v = ds.createVariable('y', int, ('y',), fill_value=-1)
    v[:4] = np.arange(4)

    v = ds.createVariable('z', 'S1', ('z', 'string3'), fill_value=b'X')
    v[...] = _char_array

    v = ds.createVariable('scalar', np.float32, ())
    v[...] = 2.0

    g = ds.createGroup('subgroup')
    v = g.createVariable('subvar', np.int32, ('x',))
    v[...] = np.arange(4.0)
    with raises(AttributeError):
        v._FillValue = -1

    ds.createDimension('mismatched_dim', 1)
    ds.createVariable('mismatched_dim', int, ())

    ds.close()


def write_h5netcdf(tmp_netcdf):
    ds = h5netcdf.Dataset(tmp_netcdf, 'w')
    ds.attrs['global'] = 42
    ds.attrs['other_attr'] = 'yes'
    ds.create_dimension('x', 4)
    ds.create_dimension('y', 5)
    ds.create_dimension('z', 6)

    v = ds.create_variable('foo', ('x', 'y'), float)
    v[...] = 1
    v.attrs['units'] = 'meters'

    v = ds.create_variable('y', ('y',), int, fillvalue=-1)
    v[:4] = np.arange(4)

    v = ds.create_variable('z', ('z', 'string3'), data=_char_array,
                           fillvalue=b'X')

    v = ds.create_variable('scalar', data=np.float32(2.0))

    g = ds.create_group('subgroup')
    v = g.create_variable('subvar', ('x',), np.int32)
    v[...] = np.arange(4.0)
    with raises(AttributeError):
        v.attrs['_FillValue'] = -1

    ds.create_dimension('mismatched_dim', 1)
    ds.create_variable('mismatched_dim', dtype=int)

    ds.close()


def read_legacy_netcdf(tmp_netcdf, read_module, write_module):
    ds = read_module.Dataset(tmp_netcdf, 'r')
    assert ds.ncattrs() == ['global', 'other_attr']
    assert ds.getncattr('global') == 42
    if not PY2 and write_module is not netCDF4:
        # skip for now: https://github.com/Unidata/netcdf4-python/issues/388
        assert ds.other_attr == 'yes'
    assert set(ds.dimensions) == set(['x', 'y', 'z', 'string3', 'mismatched_dim'])
    assert set(ds.variables) == set(['foo', 'y', 'z', 'scalar', 'mismatched_dim'])
    assert set(ds.groups) == set(['subgroup'])
    assert ds.parent is None

    v = ds.variables['foo']
    assert array_equal(v, np.ones((4, 5)))
    assert v.dtype == float
    assert v.dimensions == ('x', 'y')
    assert v.ndim == 2
    assert v.ncattrs() == ['units']
    if not PY2 and write_module is not netCDF4:
        assert v.getncattr('units') == 'meters'

    v = ds.variables['y']
    assert array_equal(v, np.r_[np.arange(4), [-1]])
    assert v.dtype == int
    assert v.dimensions == ('y',)
    assert v.ndim == 1
    assert v.ncattrs() == ['_FillValue']
    assert v.getncattr('_FillValue') == -1

    v = ds.variables['z']
    assert array_equal(v, _char_array)
    assert v.dtype == 'S1'
    assert v.ndim == 2
    assert v.dimensions == ('z', 'string3')
    assert v.ncattrs() == ['_FillValue']
    assert v.getncattr('_FillValue') == b'X'

    v = ds.variables['scalar']
    assert array_equal(v, np.array(2.0))
    assert v.dtype == 'float32'
    assert v.ndim == 0
    assert v.dimensions == ()
    assert v.ncattrs() == []

    v = ds.groups['subgroup'].variables['subvar']
    assert ds.groups['subgroup'].parent is ds
    assert array_equal(v, np.arange(4.0))
    assert v.dtype == 'int32'
    assert v.ndim == 1
    assert v.dimensions == ('x',)
    assert v.ncattrs() == []

    ds.close()


def read_h5netcdf(tmp_netcdf, write_module):
    ds = h5netcdf.Dataset(tmp_netcdf, 'r')
    assert list(ds.attrs) == ['global', 'other_attr']
    assert ds.attrs['global'] == 42
    if not PY2 and write_module is not netCDF4:
        # skip for now: https://github.com/Unidata/netcdf4-python/issues/388
        assert ds.attrs['other_attr'] == 'yes'
    assert set(ds.dimensions) == set(['x', 'y', 'z', 'string3', 'mismatched_dim'])
    assert set(ds.variables) == set(['foo', 'y', 'z', 'scalar', 'mismatched_dim'])
    assert set(ds.groups) == set(['subgroup'])
    assert ds.parent is None

    v = ds['foo']
    assert array_equal(v, np.ones((4, 5)))
    assert v.dtype == float
    assert v.dimensions == ('x', 'y')
    assert v.ndim == 2
    assert list(v.attrs) == ['units']
    if not PY2 and write_module is not netCDF4:
        assert v.attrs['units'] == 'meters'

    v = ds['y']
    assert array_equal(v, np.r_[np.arange(4), [-1]])
    assert v.dtype == int
    assert v.dimensions == ('y',)
    assert v.ndim == 1
    assert list(v.attrs) == ['_FillValue']
    assert v.attrs['_FillValue'] == -1

    v = ds['z']
    assert array_equal(v, _char_array)
    assert v.dtype == 'S1'
    assert v.ndim == 2
    assert v.dimensions == ('z', 'string3')
    assert list(v.attrs) == ['_FillValue']
    assert v.attrs['_FillValue'] == b'X'

    v = ds['scalar']
    assert array_equal(v, np.array(2.0))
    assert v.dtype == 'float32'
    assert v.ndim == 0
    assert v.dimensions == ()
    assert list(v.attrs) == []

    v = ds['subgroup']['subvar']
    assert ds['subgroup'].parent is ds
    assert array_equal(v, np.arange(4.0))
    assert v.dtype == 'int32'
    assert v.ndim == 1
    assert v.dimensions == ('x',)
    assert list(v.attrs) == []

    ds.close()


def roundtrip_legacy_netcdf(tmp_netcdf, read_module, write_module):
    write_legacy_netcdf(tmp_netcdf, write_module)
    read_legacy_netcdf(tmp_netcdf, read_module, write_module)


def test_write_legacyapi_read_netCDF4(tmp_netcdf):
    roundtrip_legacy_netcdf(tmp_netcdf, netCDF4, legacyapi)


def test_roundtrip_h5netcdf_legacyapi(tmp_netcdf):
    roundtrip_legacy_netcdf(tmp_netcdf, legacyapi, legacyapi)


def test_write_netCDF4_read_legacyapi(tmp_netcdf):
    roundtrip_legacy_netcdf(tmp_netcdf, legacyapi, netCDF4)


def test_write_h5netcdf_read_legacyapi(tmp_netcdf):
    write_h5netcdf(tmp_netcdf)
    read_legacy_netcdf(tmp_netcdf, legacyapi, h5netcdf)


def test_write_h5netcdf_read_netCDF4(tmp_netcdf):
    write_h5netcdf(tmp_netcdf)
    read_legacy_netcdf(tmp_netcdf, netCDF4, h5netcdf)


def test_roundtrip_h5netcdf(tmp_netcdf):
    write_h5netcdf(tmp_netcdf)
    read_h5netcdf(tmp_netcdf, h5netcdf)


def test_write_netCDF4_read_h5netcdf(tmp_netcdf):
    write_legacy_netcdf(tmp_netcdf, netCDF4)
    read_h5netcdf(tmp_netcdf, netCDF4)


def test_write_legacyapi_read_h5netcdf(tmp_netcdf):
    write_legacy_netcdf(tmp_netcdf, legacyapi)
    read_h5netcdf(tmp_netcdf, legacyapi)


def test_repr(tmp_netcdf):
    write_h5netcdf(tmp_netcdf)
    ds = h5netcdf.Dataset(tmp_netcdf, 'r')
    assert 'h5netcdf.core.Dataset' in repr(ds)
    assert 'subgroup' in repr(ds)
    assert 'foo' in repr(ds)
    assert 'other_attr' in repr(ds)

    assert 'h5netcdf.attrs.Attributes' in repr(ds.attrs)
    assert 'global' in repr(ds.attrs)

    assert 'h5netcdf.core.Group' in repr(ds['subgroup'])
    assert 'subvar' in repr(ds['subgroup'])

    assert 'h5netcdf.core.Variable' in repr(ds['foo'])
    assert 'float' in repr(ds['foo'])
    assert 'units' in repr(ds['foo'])
    ds.close()


def test_attrs_api(tmp_netcdf):
    with h5netcdf.Dataset(tmp_netcdf) as ds:
        ds.attrs['conventions'] = 'CF'
        ds.create_dimension('x', 1)
        v = ds.create_variable('x', ('x',), 'i4')
        v.attrs.update({'units': 'meters', 'foo': 'bar'})
    assert ds._closed
    with h5netcdf.Dataset(tmp_netcdf) as ds:
        assert len(ds.attrs) == 1
        assert dict(ds.attrs) == {'conventions': 'CF'}
        assert list(ds.attrs) == ['conventions']
        assert dict(ds['x'].attrs) == {'units': 'meters', 'foo': 'bar'}
        assert len(ds['x'].attrs) == 2
        assert sorted(ds['x'].attrs) == ['foo', 'units']


def test_optional_netcdf4_attrs(tmp_netcdf):
    with h5py.File(tmp_netcdf) as f:
        foo_data = np.arange(50).reshape(5, 10)
        f.create_dataset('foo', data=foo_data)
        f.create_dataset('x', data=np.arange(5))
        f.create_dataset('y', data=np.arange(10))
        f['foo'].dims.create_scale(f['x'])
        f['foo'].dims.create_scale(f['y'])
        f['foo'].dims[0].attach_scale(f['x'])
        f['foo'].dims[1].attach_scale(f['y'])
    with h5netcdf.Dataset(tmp_netcdf, 'r') as ds:
        assert ds['foo'].dimensions == ('x', 'y')
        assert ds.dimensions == {'x': 5, 'y': 10}
        assert array_equal(ds['foo'], foo_data)


def test_error_handling(tmp_netcdf):
    with h5netcdf.Dataset(tmp_netcdf, 'w') as ds:
        with raises(NotImplementedError):
            ds.create_dimension('x', None)
        ds.create_dimension('x', 1)
        with raises(IOError):
            ds.create_dimension('x', 2)
        ds.create_variable('x', ('x',), dtype=float)
        with raises(IOError):
            ds.create_variable('x', ('x',), dtype=float)
        ds.create_group('subgroup')
        with raises(IOError):
            ds.create_group('subgroup')


def test_invalid_netcdf4(tmp_netcdf):
    with h5py.File(tmp_netcdf) as f:
        f.create_dataset('foo', data=np.arange(5))
        # labeled dimensions but no dimension scales
        f['foo'].dims[0].label = 'x'
    with h5netcdf.Dataset(tmp_netcdf, 'r') as ds:
        with raises(ValueError):
            ds.variables['foo'].dimensions
