

import dataclasses
from collections import deque

import msgpack
import av

from .filters.abs import FilterConfAbs
from .filters.buffer import Buffer
from .filters.buffersink import BufferSink
from .filters.abuffer import ABuffer
from .filters.abuffersink import ABufferSink
from .utils import is_audio_filter, get_filter_conf_cls_nick, is_buffer_or_sink


class Graph:
    """
    in0.Buffer.out0 ->   in0.  .out0 -> in0.B.out0 -> in0.
                             A
    in0.Buffer.out0 ->   in1.  .out1 -> in0.C.out0 -> in1.
    """

    DELI = "."
    slice_size = 100
    chunk_zset_key = "graph_chunks_level:{idx}"
    chunk_amount_key = "graph_chunk_amcount:{idx}"

    def __init__(self, *input_confs: Buffer | ABuffer):
        self.avgraph = av.filter.Graph()
        self._idx = 0
        self._linking_map = {}
        self._reversed_linking_map = {}
        self._avfilters_indices = {}  # 0_filters_indices = filters + buffers + sinks
        self._in_filters = set()
        self._out_filters = set()
        self._i_buffers = []
        self._o_sinks = []
        self._filters_names = {}
        self._filters_confs = {}
        self.video = False
        self.audio = False
        #
        self.input_confs = input_confs
        return

    @property
    def configured(self):
        return self.avgraph.configured

    @property
    def n_in_filters(self):
        return len(self._in_filters)

    @property
    def n_out_filters(self):
        return len(self._out_filters)

    @property
    def avfilters_count(self):
        return len(self._avfilters_indices)

    def get_filter_conf(self, idx):
        return self._filters_confs[idx]

    def get_avfilter(self, idx):
        return self._avfilters_indices[idx]

    def get_avfilter_idx(self, name):
        return self._filters_names.get(name, None)

    def get_avfilter_by_name(self, name):
        return self.get_avfilter(self.get_avfilter_idx(name))

    def get_avfilter_name(self, idx):
        return self.get_filter_conf(idx).name

    def get_avfilter_fname(self, idx):
        return self.get_filter_conf(idx).fname

    def get_next_filter(self, fidx, input_idx):
        return self._linking_map[fidx][input_idx]

    def get_previous_filter(self, fidx, output_idx):
        return self._reversed_linking_map[fidx][output_idx]

    def has_name(self, name):
        return name in self._filters_names

    def _get_idx(self, size=1):
        tmp = self._idx
        ret = (tmp + i for i in range(size))
        self._idx += size
        return ret

    def _new_avfilter(self, idx, conf: FilterConfAbs):
        params = conf.get_avparams()
        if conf.fname == Buffer.fname:
            f = self.avgraph.add_buffer(**params)
        elif conf.fname == ABuffer.fname:
            f = self.avgraph.add_abuffer(**params)
        else:
            f = self.avgraph.add(conf.fname, **params)
        name = conf.name or f.name
        self._filters_names[name] = idx
        dup_conf = dataclasses.replace(conf)
        dup_conf.name = name
        self._filters_confs[idx] = dup_conf
        self._avfilters_indices[idx] = f
        self._linking_map[idx] = {}
        self._reversed_linking_map[idx] = {}
        return

    def add_filter(self, conf: FilterConfAbs):
        if conf.name and conf.name in self._filters_names:
            return self.get_avfilter_idx(conf.name)
        idx = next(self._get_idx(size=1))
        self._new_avfilter(idx, conf)
        return idx

    def add_filters(self, *confs: FilterConfAbs):
        indices = self._get_idx(size=len(confs))
        start_idx = None
        for idx, conf in zip(indices, confs):
            if start_idx is None:
                start_idx = idx
            self._new_avfilter(idx, conf)
        return start_idx

    def link(self, parnent_idx, child_idx, parent_out_idx=0, child_in_idx=0):
        parent = self.get_avfilter(parnent_idx)
        child = self.get_avfilter(child_idx)
        parent.link_to(child, parent_out_idx, child_in_idx)
        self._linking_map[parnent_idx][parent_out_idx] = [child_idx, child_in_idx]
        self._reversed_linking_map[child_idx][child_in_idx] = [parnent_idx, parent_out_idx]
        return

    def link_by_names(self, parnent_name, child_name, parent_out_idx=0, child_in_idx=0):
        parnent_idx = self.get_avfilter_idx(parnent_name)
        child_idx = self.get_avfilter_idx(child_name)
        return self.link(parnent_idx, child_idx, parent_out_idx=parent_out_idx, child_in_idx=child_in_idx)

    def _add_input(self, filter_idx, buffer_conf: Buffer | ABuffer, input_idx=0):
        """
        buffer.out0 -> in_idx.filter
        """
        buffer_idx = self.add_filter(buffer_conf)
        self.link(buffer_idx, filter_idx, 0, input_idx)
        self._i_buffers.append(buffer_idx)
        self._in_filters.add(filter_idx)
        return buffer_idx

    def add_input(self, filter_idx, buffer_conf, input_idx=0):
        return self._add_input(filter_idx, buffer_conf, input_idx)

    def add_input_template(self, filter_idx, template, input_idx=0):
        if template.type == "audio":
            conf = ABuffer(template=template)
        else:
            conf = Buffer(template=template)
        return self.add_input(filter_idx, conf, input_idx)

    def add_output(self, filter_idx, output_idx=0, name=None):
        """
        filter.out_idx -> in0.sink
        """
        out_fobj = self.get_avfilter(filter_idx)
        if is_audio_filter(out_fobj.name):
            self.audio = True
            sink_idx = self.add_filter(ABufferSink(name=name))
        else:
            self.video = True
            sink_idx = self.add_filter(BufferSink(name=name))
        self.link(filter_idx, sink_idx, output_idx, 0)
        self._o_sinks.append(sink_idx)
        self._out_filters.add(filter_idx)
        return sink_idx

    def _link_filters(self, *filters: FilterConfAbs):
        end_idx = start_idx = parent_idx = self.add_filters(*filters)
        for i in range(1, len(filters)):
            end_idx = start_idx + i
            self.link(parent_idx, end_idx)
            parent_idx = end_idx
        return start_idx, end_idx

    def link_filters(self, *filters: FilterConfAbs):
        return self._link_filters(*filters)

    def set_outputs(self):
        if not self._o_sinks:
            linking_keys = list(self._linking_map.keys())
            for idx in linking_keys:
                outgoing = self._linking_map[idx]
                avf = self.get_avfilter(idx)
                outputs = avf.outputs
                if len(outgoing) == len(outputs):
                    continue
                for i in range(len(outputs)):
                    if i in outgoing:
                        continue
                    self.add_output(idx, i)
        return

    def set_inputs(self, *input_confs):
        if not self._i_buffers and input_confs:
            conf_idx = 0
            reversed_keys = list(self._reversed_linking_map.keys())
            for idx in reversed_keys:
                incoming = self._reversed_linking_map[idx]
                avf = self.get_avfilter(idx)
                inputs = avf.inputs
                if len(incoming) == len(inputs):
                    continue
                for i in range(len(inputs)):
                    if i in incoming:
                        continue
                    self.add_input(idx, input_confs[conf_idx], i)
                    conf_idx += 1
        return

    def mark_input_output(self, *input_confs):
        input_confs = input_confs or self.input_confs
        self.set_inputs(*input_confs)
        self.set_outputs()
        return

    def configure(self, *input_confs):
        if self.configured:
            return
        self.mark_input_output(*input_confs)
        if not self.avgraph.configured:
            self.avgraph.configure()
        return

    def _push_pull(self, inputs_map: dict):
        for idx in self._i_buffers:
            if idx not in inputs_map:
                continue
            self.get_avfilter(idx).push(inputs_map[idx])
        frames = []
        for sink_idx in self._o_sinks:
            sink_f = self.get_avfilter(sink_idx)
            try:
                frame = sink_f.pull()
            except av.error.BlockingIOError:
                frames.append(None)
            else:
                frames.append(frame)
        return frames

    def apply(self, inputs_map: dict):
        # inputs_map={buffer0: frame0, buffer1: frame1, ...}
        self.configure()
        return self._push_pull(inputs_map)

    def apply_frames(self, *frames):
        self.configure()
        inputs_map = {}
        for idx, frame in zip(self._i_buffers, frames):
            inputs_map[idx] = frame
        return self._push_pull(inputs_map)

    @property
    def sink_input_tb(self):
        f = self.get_avfilter(self._o_sinks[0])
        return f.get_input_tb(0)

    @property
    def sink_input_frame_rate(self):
        f = self.get_avfilter(self._o_sinks[0])
        return f.get_input_frame_rate(0)

    @property
    def nb_threads(self):
        return self.avgraph.nb_threads

    @nb_threads.setter
    def nb_threads(self, n):
        self.avgraph.nb_threads = n
        return

    @classmethod
    def get_filter_str_key(cls, nickname=None, gname=None, in_idx=None, out_idx=None, params_str=None):
        in_idx = in_idx or ""
        out_idx = out_idx or ""
        gname = gname or ""
        nickname = nickname or ""
        params_str = params_str or ""
        return f"{in_idx}{cls.DELI}{nickname}{cls.DELI}{gname}{cls.DELI}{out_idx}{cls.DELI}{params_str}"

    @classmethod
    def split_fstr(cls, fstr):
        # TODO: walk through one by one from left to right
        in_idx, fname, gname, out_idx, params_str = fstr.split(f"{cls.DELI}")
        in_idx = 0 if not in_idx else int(in_idx)
        out_idx = 0 if not out_idx else int(out_idx)
        gname = gname if gname else None
        return in_idx, fname, gname, out_idx, params_str

    def preorder_traversal(self):
        nodes_map = {}
        ncount = 0
        fidx = list(self._out_filters)[0]
        out_idx = list(self._linking_map[fidx])[0]
        branch = deque([])
        branches = []
        stack = deque([[fidx, out_idx, branch]])
        leaves = []  # leaves(filters or buffers) will be enqueued in preorder traversal
        while stack:
            fidx, out_idx, branch = stack.popleft()
            if fidx is None:
                leaves.append(list(branch))
                continue
            fobj = self.get_avfilter(fidx)
            conf = self.get_filter_conf(fidx)
            if fidx in nodes_map:
                name = nodes_map[fidx]
                key = self.get_filter_str_key(gname=name, out_idx=out_idx)
                branch.appendleft(key)
                branches.append(list(branch))
                continue
            if len(fobj.inputs) > 1 or len(fobj.outputs) > 1:
                name = f"N{ncount}"
                ncount += 1
                nodes_map[fidx] = name
            if not self._reversed_linking_map[fidx]:
                if is_buffer_or_sink(conf.fname):
                    leaves.append([conf.name, 0])
                    child_idx, child_in_idx = self._linking_map[fidx][0]
                    if child_in_idx == 0:
                        branches.append(list(branch))
                else:
                    gname = nodes_map.get(fidx, None)
                    params_str = conf.to_params_str(need_name=False)
                    key = self.get_filter_str_key(conf.nick_name, gname=gname, params_str=params_str)
                    branch.appendleft(key)
                    branches.append(list(branch))
                    for i in range(len(fobj.inputs)):
                        leaves.append([conf.name, i])
                continue
            if len(fobj.inputs) > 1:
                gname = nodes_map[fidx]
                parents = self._reversed_linking_map[fidx]
                for i in range(1, len(fobj.inputs)):
                    if i not in parents:
                        stack.appendleft([None, None, deque([conf.name, i])])
                        continue
                    parent_idx, parent_out_idx = parents[i]
                    key = self.get_filter_str_key(gname=gname, in_idx=i)
                    stack.appendleft([parent_idx, parent_out_idx, deque([key])])
                parent_idx, parent_out_idx = parents[0]
                params_str = conf.to_params_str(need_name=False)
                key = self.get_filter_str_key(conf.nick_name, gname=gname, params_str=params_str)
                branch.appendleft(key)
                stack.appendleft([parent_idx, parent_out_idx, branch])
                continue
            gname = nodes_map.get(fidx, None)
            params_str = conf.to_params_str(need_name=False)
            in_idx = list(self._reversed_linking_map[fidx].keys())[0]
            key = self.get_filter_str_key(conf.nick_name, in_idx=in_idx, gname=gname, params_str=params_str)
            branch.appendleft(key)
            parent_idx, parent_out_idx = self._reversed_linking_map[fidx][in_idx]
            stack.appendleft([parent_idx, parent_out_idx, branch])
        return branches, leaves

    @classmethod
    def from_branches(cls, branches):
        g = cls()
        for branch in branches:
            parent_str = branch[0]
            in_idx, nick_name, gname, out_idx, params_str = cls.split_fstr(parent_str)
            if nick_name:
                fcls = get_filter_conf_cls_nick(nick_name)
                parent = fcls.from_params_str(params_str, name=gname)
                parent_idx = g.add_filter(parent)
            else:
                parent_idx = g.get_avfilter_idx(gname)
            parent_out_idx = out_idx
            for i in range(1, len(branch)):
                fstr = branch[i]
                in_idx, nick_name, gname, out_idx, params_str = cls.split_fstr(fstr)
                in_idx = 0 if not in_idx else int(in_idx)
                if nick_name:
                    fcls = get_filter_conf_cls_nick(nick_name)
                    f = fcls.from_params_str(params_str, name=gname)
                    fidx = g.add_filter(f)
                else:
                    fidx = g.get_avfilter_idx(gname)
                g.link(parent_idx, fidx, parent_out_idx, in_idx)
                parent_idx = fidx
                parent_out_idx = out_idx
        return g

    def serialize(self):
        self.set_outputs()
        if len(self._out_filters) > 1 or len(self._o_sinks) > 1:
            raise KeyError("do not support serialize a graph with more than one sinks")
        branches, leaves = self.preorder_traversal()
        return msgpack.dumps(branches), leaves

    @classmethod
    def deserialize(cls, branches):
        if type(branches) == bytes:
            branches = msgpack.loads(branches)
        g = cls.from_branches(branches)
        return g


def main():
    return


if __name__ == "__main__":
    main()
