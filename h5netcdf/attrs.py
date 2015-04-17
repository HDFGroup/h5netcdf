from collections import MutableMapping


class HasAttributesMixin(object):
    def getncattr(self, name):
        return self.attrs[name]

    def setncattr(self, name, value):
        self.attrs[name] = value

    def ncattrs(self):
        return list(self.attrs)

    def __getattr__(self, name):
        return self.attrs[name]

    def __setattr__(self, name, value):
        if self._initialized and name not in self.__dict__:
            self.attrs[name] = value
        else:
            object.__setattr__(self, name, value)


_hidden_attrs = frozenset(['REFERENCE_LIST', 'CLASS', 'DIMENSION_LIST', 'NAME',
                           '_Netcdf4Dimid', '_Netcdf4Coordinates',
                           '_nc3_strict'])
_reserved_attrs = _hidden_attrs | frozenset(['_FillValue'])


class Attributes(MutableMapping):
    def __init__(self, h5attrs):
        self._h5attrs = h5attrs

    def __getitem__(self, key):
        if key in _hidden_attrs:
            raise KeyError(key)
        return self._h5attrs[key]

    def __setitem__(self, key, value):
        if key in _reserved_attrs:
            raise AttributeError('cannot write attribute with reserved name %r'
                                 % key)
        self._h5attrs[key] = value

    def __delitem__(self, key):
        del self._h5attrs[key]

    def __iter__(self):
        for key in self._h5attrs:
            if key not in _hidden_attrs:
                yield key

    def __len__(self):
        hidden_count = sum(1 if attr in self._h5attrs else 0
                           for attr in _hidden_attrs)
        return len(self._h5attrs) - hidden_count

    def __repr__(self):
        return '\n'.join(['<h5netcdf.%s>' % type(self).__name__] +
                         ['%s: %r' % (k, v) for k, v in self.items()])
