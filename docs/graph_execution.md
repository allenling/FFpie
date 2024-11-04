
# Graph

FFmpeg-n4.1.1.

here we take the command below as the example to show you how a graph executes.

```
ffmpeg -i input_video.mp4 -filter_complex "[0:a]atempo=2.0[a]" -map "[a]" -y output.mp4
```

and the graph would be like

```

abuffer ---> aresample_0 ---> atempo ---> aresample_1 ---> aformat ---> abuffersink

```

why? see `how_FFmpeg_speeds_up_a_video.md`.

# the invoking chain

when FFmpeg decodes a frame out of the packets, it will send it to the graph, the invoking chains is like

```
decode_audio -> send_frame_to_filters -> ifilter_send_frame -> av_buffersrc_add_frame_flags -> ff_filter_frame
                                                                                            -> push_frame
```

`ifilter_send_frame` will pass `ifilter->filter`, which is the abuffer filter,  to `av_buffersrc_add_frame_flags`, and in
`av_buffersrc_add_frame_flags`, FFmpeg will run some checks on the output link and the decoded frame to make sure that they
match.

```c
static int ifilter_send_frame(InputFilter *ifilter, AVFrame *frame)
{
    ret = av_buffersrc_add_frame_flags(ifilter->filter, frame, AV_BUFFERSRC_FLAG_PUSH);
}

int attribute_align_arg av_buffersrc_add_frame_flags(AVFilterContext *ctx, AVFrame *frame, int flags)
{
    ret = ff_filter_frame(ctx->outputs[0], copy);
    if (ret < 0)
        return ret;

    if ((flags & AV_BUFFERSRC_FLAG_PUSH)) {
        ret = push_frame(ctx->graph);
        if (ret < 0)
            return ret;
    }
}
```

that `ctx` is the reference of the `abuffer` filter, and its `outputs[0]` is the link from `abuffer` to the `aresample_0`,
`copy` is a copy of the decoded frame.

so if your decoded frame has meta different from those in graph construction, then it is not allowed.

```c
int ff_filter_frame(AVFilterLink *link, AVFrame *frame)
{
    int ret;
    FF_TPRINTF_START(NULL, filter_frame); ff_tlog_link(NULL, link, 1); ff_tlog(NULL, " "); ff_tlog_ref(NULL, frame, 1);

    /* Consistency checks */
    if (link->type == AVMEDIA_TYPE_VIDEO) {
    } else {
        if (frame->format != link->format) {
            av_log(link->dst, AV_LOG_ERROR, "Format change is not supported\n");
            goto error;
        }
        if (frame->channels != link->channels) {
            av_log(link->dst, AV_LOG_ERROR, "Channel count change is not supported\n");
            goto error;
        }
        if (frame->channel_layout != link->channel_layout) {
            av_log(link->dst, AV_LOG_ERROR, "Channel layout change is not supported\n");
            goto error;
        }
        if (frame->sample_rate != link->sample_rate) {
            av_log(link->dst, AV_LOG_ERROR, "Sample rate change is not supported\n");
            goto error;
        }
    }
}
```

FFmpeg will compare formats, channels, and smaple_rates in both parts, and raise errors if they are not equal.

# push_frame

`push_frame` will actually run the graph in a while loop until an error occur.

```c
static int push_frame(AVFilterGraph *graph)
{
    int ret;

    while (1) {
        ret = ff_filter_graph_run_once(graph);
        if (ret == AVERROR(EAGAIN))
            break;
        if (ret < 0)
            return ret;
    }
    return 0;
}
```

`ff_filter_graph_run_once` will iterate over all fitlers and try to find if there is any filter that is ready to run.

if there's at least one ready filter, then run it.

a filter that is ready if it has a `ready` attribute that's greater than 0.

basically `ready` represents the priority of a filter, larger `ready`, heigher priority.

there are a couple possible values for `ready`, we have seen some of them like 100, 200, 300, and they are used for different
purposes.

and 300 is also the priority that indicates that the filter has to be run once, maybe there's some leftovers in it, or it's
triggered by someone, like its parent, etc.

and when sending a frame to the graph, FFmpeg will first mark the first filter as `ready` by setting its `ready` to be 300
at the end of `ff_filter_frame`, and push the decoded frame into the link.

```c
void ff_filter_set_ready(AVFilterContext *filter, unsigned priority)
{
    filter->ready = FFMAX(filter->ready, priority);
}

int ff_filter_frame(AVFilterLink *link, AVFrame *frame)
{
    // the link has the buffer at the head of the link, and the end of the link points to the aresample_0. 
    ret = ff_framequeue_add(&link->fifo, frame);
    if (ret < 0) {
        av_frame_free(&frame);
        return ret;
    }
    ff_filter_set_ready(link->dst, 300);
    return 0;
}
```

here `link->dst` is pointing from the `abuffer` to the `aresample_0`, so the `aresample_0` is marked as 300.

and in `ff_filter_graph_run_once`, if there's more than one filters that have the heighest priority, then they will be
executed in the order of being appending to the array `graph->filters`.

```c
int ff_filter_graph_run_once(AVFilterGraph *graph)
{
    AVFilterContext *filter;
    unsigned i;

    av_assert0(graph->nb_filters);
    filter = graph->filters[0];
    for (i = 1; i < graph->nb_filters; i++)
        if (graph->filters[i]->ready > filter->ready)
            filter = graph->filters[i];
    if (!filter->ready)
        return AVERROR(EAGAIN);
    return ff_filter_activate(filter);
}

```

the variable `filter` is pointing to the first filter in the graph, which is the `atempo` in our case, and then iterate through
the array `filters`, and find a filter that has a heigher priority, and replace the variable `filter` with that filter.

and as we know, there's one filter whose priority is heigher than the `atempo`, which is `aresample_0`.

# ff_filter_activate

`ff_filter_activate` will call the `activate` function in the filter, if a filter has not defined a `activate` function,
then go to `ff_filter_activate_default`. 

and one more thing, `ff_filter_activate` will reset the `ready` for the filter to 0!

```c
int ff_filter_activate(AVFilterContext *filter)
{
    int ret;

    /* Generic timeline support is not yet implemented but should be easy */
    av_assert1(!(filter->filter->flags & AVFILTER_FLAG_SUPPORT_TIMELINE_GENERIC &&
                 filter->filter->activate));
    filter->ready = 0;
    ret = filter->filter->activate ? filter->filter->activate(filter) :
          ff_filter_activate_default(filter);
    if (ret == FFERROR_NOT_READY)
        ret = 0;
    return ret;
}
```

most filters you encounter probably has no `activate` function, so let's see how `ff_filter_activate_default` works.

```c
static int ff_filter_activate_default(AVFilterContext *filter)
{
    unsigned i;

    for (i = 0; i < filter->nb_inputs; i++) {
        if (samples_ready(filter->inputs[i], filter->inputs[i]->min_samples)) {
            return ff_filter_frame_to_filter(filter->inputs[i]);
        }
    }
}
```

`samples_ready` will check if the samples stored in the queue is greater than the min_samples, by defaults, which is 0.

for the `min_samples`, FFmpeg says

```c
    /**
     * Minimum number of samples to filter at once. If filter_frame() is
     * called with fewer samples, it will accumulate them in partial_buf.
     * This field and the related ones must not be changed after filtering
     * has started.
     * If 0, all related fields are ignored.
     */
    int min_samples;
```

and `samples_ready` invokes `ff_framequeue_queued_samples` to get the samples in the queue.

```c
/**
 * Get the number of queued frames.
 */
static inline size_t ff_framequeue_queued_frames(const FFFrameQueue *fq)
{
    return fq->queued;
}
/**
 * Get the number of queued samples.
 */
static inline uint64_t ff_framequeue_queued_samples(const FFFrameQueue *fq)
{
    return fq->total_samples_head - fq->total_samples_tail;
}
static int samples_ready(AVFilterLink *link, unsigned min)
{
    return ff_framequeue_queued_frames(&link->fifo) &&
           (ff_framequeue_queued_samples(&link->fifo) >= min ||
            link->status_in);
}
```

# ff_filter_frame_to_filter

what `ff_filter_frame_to_filter` does just check if there's samples need to be process, if no, then just return, else just call
the `filter_frame` function in the filter with that decoded frame as the argument.

and it will also re-activiate the filter, why? see the comments.

```c
static int ff_filter_frame_to_filter(AVFilterLink *link)
{
    ret = link->min_samples ?
          ff_inlink_consume_samples(link, link->min_samples, link->max_samples, &frame) :
          ff_inlink_consume_frame(link, &frame);
    av_assert1(ret);
    if (ret < 0) {
        av_assert1(!frame);
        return ret;
    }
    
    ret = ff_filter_frame_framed(link, frame);
    if (ret < 0 && ret != link->status_out) {
        ff_avfilter_link_set_out_status(link, ret, AV_NOPTS_VALUE);
    } else {
        /* Run once again, to see if several frames were available, or if
           the input status has also changed, or any other reason. */
        ff_filter_set_ready(dst, 300);
    }
    return ret;
}
```

but if we always re-activiate a filter when finish it, you will get a deal loop, we will be stuck in the loop forever since
there's always a filter that's ready.

but this won't happen because FFmpeg will not re-activiate a filter if it has nothing to do, for instance, there's no more
samples for `atempo` to process, then FFmpeg will just return instead of going to the end to activiate it.

and here the `filter_frame` for `aresample` will call `ff_filter_frame` to notify the next filter, which is going to be
the `atempo`.

```c
static int filter_frame(AVFilterLink *inlink, AVFrame *insamplesref)
{
    ret = ff_filter_frame(outlink, outsamplesref);
    av_frame_free(&insamplesref);
    return ret;
}
```

# execution loop summary

the diagram shows how the filters get executed.

```
                     
when processing the first frame, and there's no samples out from atempo:

filters of 300        |    the filter that gets executed
-----------------------------------------------------------------
[aresample_0]              aresample_0, it will mark atempo as 300, and re-activiate itself.

[atempo,aresample_0]       atempo, because atempo is located at the index prior to aresample_0, and re-activiate itself.

[atempo,aresample_0]       atempo, this time, no more data for atempo, so it won't re-activiate itself.

[aresample_0]              aresample_0, and aresample_0 has thing to do, return.

[]                         no ready frame, return.



when sending the fourth frame to the graph, atempo will throw out 512 samples, and notify the next filter:


filters of 300                   |    the filter that gets executed
-----------------------------------------------------------------

[aresample_0]                          aresample_0

[atempo,aresample_0]                   atempo

[atempo,aresample_0,aresample_1]       atempo

[aresample_0,aresample_1]              aresample_0

[aresample_1]                          aresample_1

[aformat,aresample_1]                  aformat

[abuffersink,aformat,aresample_1]      abuffersink, because abuffersink was being appended before the time the aformat enqueued

[aformat,aresample_1]                  aformat

[aresample_1]                          aresample_1

[]                                     return

```


# two or more input buffers

how FFmpeg handles multiple inputs for a graph?

in summary, at first, FFmpeg will not run the configuration for the graph, and it will wait until every stream has produced
the first frame, it will store the first frame of every input stream except the last one in cache somewhere.

and once FFmpeg has decoded the first frame from the last input stream, move those cached frames from `ifilters` to the queue
of their links, then run the graph.

for subsequent frames, everytime FFmpeg gets one decoded frame, and it will push it into the graph and run the graph immediately.

here we take the below command as the eaxmple to explain how in details.

```
ffmpeg -i input1.mp4 -i input2.mp4 -filter_complex [0:v][1:v]hstack=inputs=2[v] -map [v] -y output.mp4
```

the invoking chain is going to be

```
decode_audio/decode_video -> send_frame_to_filters -> ifilter_send_frame -> configure_filtergraph
```

in `ifilter_send_frame`, FFmpeg will check if all the formats are known so far.

```c
// Filters can be configured only if the formats of all inputs are known.
static int ifilter_has_all_input_formats(FilterGraph *fg)
{
    int i;
    for (i = 0; i < fg->nb_inputs; i++) {
        if (fg->inputs[i]->format < 0 && (fg->inputs[i]->type == AVMEDIA_TYPE_AUDIO ||
                                          fg->inputs[i]->type == AVMEDIA_TYPE_VIDEO))
            return 0;
    }
    return 1;
}
static int ifilter_send_frame(InputFilter *ifilter, AVFrame *frame)
{
    if (need_reinit) {
        ret = ifilter_parameters_from_frame(ifilter, frame);
        if (ret < 0)
            return ret;
    }
    if (need_reinit || !fg->graph) {
        for (i = 0; i < fg->nb_inputs; i++) {
            if (!ifilter_has_all_input_formats(fg)) {
                AVFrame *tmp = av_frame_clone(frame);
                if (!tmp)
                    return AVERROR(ENOMEM);
                av_frame_unref(frame);

                if (!av_fifo_space(ifilter->frame_queue)) {
                    ret = av_fifo_realloc2(ifilter->frame_queue, 2 * av_fifo_size(ifilter->frame_queue));
                    if (ret < 0) {
                        av_frame_free(&tmp);
                        return ret;
                    }
                }
                av_fifo_generic_write(ifilter->frame_queue, &tmp, sizeof(tmp), NULL);
                return 0;
            }
        }
        ret = configure_filtergraph(fg);
    }
}
```

when FFmpeg decodes the first frame from the first input file, then it finds that the format for the second buffer filter is not
decided.

remember that `ifilter->format` was decided in the function `ifilter_parameters_from_frame` right above the `if` statement.

then it will put the frame into the cache of the `ifilter`, which is `ifilter->frame_queue`, by the function `av_fifo_generic_write`,
and return.

and then when FFmpeg gets the first frame from the second input file, all the formats are known, then go to the function
`configure_filtergraph` to initialize the graph.

and in `configure_filtergraph`, FFmpeg will try to take the frames in the cache of each `ifilter`, after adding buffers and
buffersink filter.

```c
int configure_filtergraph(FilterGraph *fg)
{
    if ((ret = avfilter_graph_config(fg->graph, NULL)) < 0)
        goto fail;

    // here!!!!!!!!!!!!!!!!!
    for (i = 0; i < fg->nb_inputs; i++) {
        while (av_fifo_size(fg->inputs[i]->frame_queue)) {
            AVFrame *tmp;
            av_fifo_generic_read(fg->inputs[i]->frame_queue, &tmp, sizeof(tmp), NULL);
            ret = av_buffersrc_add_frame(fg->inputs[i]->filter, tmp);
            av_frame_free(&tmp);
            if (ret < 0)
                goto fail;
        }
    }
}
```

FFmpeg takes out the frame in the `fg->inputs[i]->frame_queue`, which is the frame_queue of the first input stream, and call
the function `av_buffersrc_add_frame` to put that frame into the queue of the output link of the buffer filter, and set
the `dst` of the link, in our case this is the `hstack` filter, as `ready` state.

though `av_buffersrc_add_frame` will trigger the graph to run, `av_buffersrc_add_frame` will invoke the function
`av_buffersrc_add_frame_flags` with a flag of 0 to prevent the graph from running.

```c
int attribute_align_arg av_buffersrc_add_frame(AVFilterContext *ctx, AVFrame *frame)
{
    return av_buffersrc_add_frame_flags(ctx, frame, 0);
}
```

and `av_buffersrc_add_frame_flags` will only run the graph if the last parameter, the flag, is 4, or `AV_BUFFERSRC_FLAG_PUSH`.

```c
enum {

    AV_BUFFERSRC_FLAG_PUSH = 4,

};
int attribute_align_arg av_buffersrc_add_frame_flags(AVFilterContext *ctx, AVFrame *frame, int flags)
{
    if ((flags & AV_BUFFERSRC_FLAG_PUSH)) {
        ret = push_frame(ctx->graph);
        if (ret < 0)
            return ret;
    }
}
```

and then FFmpeg will call the function `av_buffersrc_add_frame_flags` with a flag of 4 at the end of the function
`ifilter_send_frame`, to put the first frame of the second input file to the link, and then finally get to the
funciton `ff_filter_graph_run_once` to run the graph.

```c
static int ifilter_send_frame(InputFilter *ifilter, AVFrame *frame)
{
    if (need_reinit || !fg->graph) {
    }
    ret = av_buffersrc_add_frame_flags(ifilter->filter, frame, AV_BUFFERSRC_FLAG_PUSH);
}
```

next time, when the second frame out from the first input stream comes into `configure_filtergraph`, FFmpeg will skip over the
configuration, and call the function `av_buffersrc_add_frame_flags` at the end to run the graph.

and the `hstack` filter will return instantly if it finds out that not all the frames are ready.


