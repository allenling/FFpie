



from ffpie.graph.filters import abs
from ffpie.graph.filters.buffer import Buffer
from ffpie.graph.filters.abuffer import ABuffer
from ffpie.graph.filters.buffersink import BufferSink
from ffpie.graph.filters.abuffersink import ABufferSink

from . import filters


BUFFER_SINK_SETS = {Buffer.fname, ABuffer.fname, BufferSink.fname, ABufferSink.fname}


def is_filter_supported(fname):
    return abs.FILTERS_MAP.get(fname, None) is not None


def is_audio_filter(fname):
    return is_filter_supported(fname) and fname in abs.AUDIO_FILTERS


def get_cls(cls_name):
    return getattr(filters, cls_name, None)


def get_filter_conf_cls(fname):
    cls_name = abs.FILTERS_MAP.get(fname, None)
    if not cls_name:
        return
    return get_cls(cls_name)


def get_filter_conf_cls_nick(nick_fname):
    cls_name = abs.NICK_NAMES_MAP.get(nick_fname, None)
    if not cls_name:
        return
    return get_cls(cls_name)


def get_filter_conf_obj(fname, **params):
    return get_filter_conf_cls(fname)(**params)


def get_filter_inputs_count(fname):
    return get_filter_conf_cls(fname).inputs_count


def get_filter_outputs_count(fname):
    return get_filter_conf_cls(fname).outputs_count


def get_filter_params_keys(fname):
    return set(get_filter_conf_cls(fname).__dataclass_fields__.keys())


def is_buffer_or_sink(fname):
    return fname in BUFFER_SINK_SETS


def main():
    return


if __name__ == "__main__":
    main()
