

# Speed up a video file

speeding up a video involves speeding up both the video track/stream the audio track/stream.

FFmpeg has two filters that help you do that, which are setpts and atempo, and the former one is for dealing with video frames
and the latter one is for audio frames.

next we are going to dive into the source code of FFmpeg to explain the working flow of FFmpeg. 

and the source code version is pinned to n4.4.1.

note: when quote the code from FFmpeg, we would not copy all lines of code, we will only take the lines that are most
important and omit others.

# Speed up the audio track

the command is as follows:

```
ffmpeg -i input_video.mp4 -filter_complex "[0:a]atempo=2.0[a]" -map "[a]" -y output.mp4
```

actually when the graph finishes its initalization, the entire graph will become:

```

abuffer ---> aresample_0 ---> atempo ---> aresample_1 ---> aformat ---> abuffersink

```

there will be 6 filters, not 3 as you might expect, in our graph finally.

FFmpeg will insert more filters into the graph along not just the atempo we specify in the complex_filter string.

let's see how and when they are being added.

## Variables and constants

let's first list some constants in FFmpeg here in case we forget.

the audio formats that FFmpeg supports are as follows:

```c
enum AVSampleFormat {
    AV_SAMPLE_FMT_NONE = -1,
    AV_SAMPLE_FMT_U8,          ///< unsigned 8 bits
    AV_SAMPLE_FMT_S16,         ///< signed 16 bits
    AV_SAMPLE_FMT_S32,         ///< signed 32 bits
    AV_SAMPLE_FMT_FLT,         ///< float
    AV_SAMPLE_FMT_DBL,         ///< double

    AV_SAMPLE_FMT_U8P,         ///< unsigned 8 bits, planar
    AV_SAMPLE_FMT_S16P,        ///< signed 16 bits, planar
    AV_SAMPLE_FMT_S32P,        ///< signed 32 bits, planar
    AV_SAMPLE_FMT_FLTP,        ///< float, planar
    AV_SAMPLE_FMT_DBLP,        ///< double, planar
    AV_SAMPLE_FMT_S64,         ///< signed 64 bits
    AV_SAMPLE_FMT_S64P,        ///< signed 64 bits, planar

    AV_SAMPLE_FMT_NB           ///< Number of sample formats. DO NOT USE if linking dynamically
};
```

so when you see a format somewhere whose value is 8, it means FLTP format.

and all filters are put together in the list `filter_list`, you can go there directly to search the filter name you want 
to look up for.

```c
static const AVFilter * const filter_list[] = {
    &ff_af_abench,
    &ff_af_acompressor,
    &ff_af_acontrast,
    &ff_af_acopy,
    &ff_af_acue,
    ...
}
```

## links

links just an arrow line that come out from the output of a filter, then point to the input of another filter.

```

    f1.out1  ----link A-----> in1.f2
       out2  ----link B-----> in1.f3

```

f1 is called the source of the link, and f2 and f3 are called the dest of the link, the source and the dest are stored in 
`link->src` and `link->dst` respectively.

basically a link saves the format, and the width, the height, and other meta information for the frame from the source to the dest.

for instance, if `link->format` is set up to be FLTP, meaning the audio frame produced by the source is going to be FLTP, and the
dest filter will accept a FLTP frame. 


## The flow

when the first frame is being sent to the graph, FFmpeg will start to initialize the graph.

the invoking chain would be:

```

decode_audio -> send_frame_to_filters -> ifilter_send_frame -> configure_filtergraph

```

`ifilter_send_frame` will check if we need to reinit the graph or the graph is still uninitialized.

```c

static int ifilter_send_frame(InputFilter *ifilter, AVFrame *frame)
{
    if (need_reinit || !fg->graph) {
        ret = configure_filtergraph(fg);
    }
}
```

## configure_filtergraph

and the `configure_filtergraph` function will detect the number of the inputs and outputs, add the first and the last filter
into the graph, and then configure the graph.

```c
int configure_filtergraph(FilterGraph *fg)
{
    for (cur = inputs, i = 0; cur; cur = cur->next, i++)
        if ((ret = configure_input_filter(fg, fg->inputs[i], cur)) < 0) {
            avfilter_inout_free(&inputs);
            avfilter_inout_free(&outputs);
            goto fail;
        }
    avfilter_inout_free(&inputs);

    for (cur = outputs, i = 0; cur; cur = cur->next, i++)
        configure_output_filter(fg, fg->outputs[i], cur);
    avfilter_inout_free(&outputs);
}
```

variable `inputs` represents the number of input streams, in our case, we only have one input stream, which is the audio stream.

`configure_input_filter` will call `configure_input_audio_filter` to insert an audio input filter and configure it , and call
`configure_input_video_filter` for a video input filter if the graph is type of video.

## configure_input_audio_filter

as its name suggests, here FFmpeg will insert an abuffer filter to the head of graph.

first, it will allocate space for an abuffer filter.

```c

const AVFilter *abuffer_filt = avfilter_get_by_name("abuffer");

```

then add that abuffer into the graph.

```c
    if ((ret = avfilter_graph_create_filter(&ifilter->filter, abuffer_filt,
                                            name, args.str, NULL,
                                            fg->graph)) < 0)
        return ret;
```

here the `args.str` is as follows:

```
"time_base=1/44100:sample_rate=44100:sample_fmt=fltp:channel_layout=0x3"
```

these are the options that are used to initialize the abuffer filter, and where are they from?

the `arg` is constructed by `ifilter`:

```c
    av_bprintf(&args, "time_base=%d/%d:sample_rate=%d:sample_fmt=%s",
             1, ifilter->sample_rate,
             ifilter->sample_rate,
             av_get_sample_fmt_name(ifilter->format));
```

this `ifilter` is not a real filter, it is a structure that contains a series of configuration for the input of the graph that
FFmpeg has when opening the input file.

put it simply, this is the meta info extracted from your input file, and its attributes will be filled in when the first frame
was decoded.

the invoking chain

```
decode_audio/decode_video -> send_frame_to_filters -> ifilter_send_frame -> ifilter_parameters_from_frame

```

in `ifilter_send_frame`, FFmpeg will check if we need to initialize or re-initialize the graph.

if the parameters for the frame and for the `ifilter` are different, then redo initialization through `ifilter_parameters_from_frame`.

in `ifilter_parameters_from_frame`, FFmpeg will copy related attributes to the ifilter from the first frame.

```c

static int ifilter_send_frame(InputFilter *ifilter, AVFrame *frame)
{   
    /* determine if the parameters for this input changed */
    need_reinit = ifilter->format != frame->format;
    // other if checks ommited.
    if (need_reinit) {
        ret = ifilter_parameters_from_frame(ifilter, frame);
        if (ret < 0)
            return ret;
    }
}

int ifilter_parameters_from_frame(InputFilter *ifilter, const AVFrame *frame)
{

    av_buffer_unref(&ifilter->hw_frames_ctx);

    ifilter->format = frame->format;

    ifilter->width               = frame->width;
    ifilter->height              = frame->height;
    ifilter->sample_aspect_ratio = frame->sample_aspect_ratio;

    ifilter->sample_rate         = frame->sample_rate;
    ifilter->channels            = frame->channels;
    ifilter->channel_layout      = frame->channel_layout;

    if (frame->hw_frames_ctx) {
        ifilter->hw_frames_ctx = av_buffer_ref(frame->hw_frames_ctx);
        if (!ifilter->hw_frames_ctx)
            return AVERROR(ENOMEM);
    }

    return 0;
}
```

so `ifilter` containes the configurations for your input file.

here `ifilter->format` is 8 representing a format of FLTP. (please check the section `constants`)

so `abuffer` will output frames of a format of FLTP as abuffer has no input filter, and more precisely, it will only accept
FLTP type of frames since abuffer does not do anything but just transfers frames to its next filter.

and `avfilter_graph_create_filter` will also add the `abuffer` into the array `fg->graph->filters`.

basically all filters of a graph will be stored in `AVFilterGraph->filters`, which is an array of pointers.

you can visit the ith filter by calling `AVFilterGraph->filters[i]`.

and then link the abuffer to the atempo.

```c
    // here, last_filter is the atempo.
    if ((ret = avfilter_link(last_filter, 0, in->filter_ctx, in->pad_idx)) < 0)
        return ret;
```

and if you want to speed up a just a portion of your audio that does not start at time 0, in `configure_input_audio_filter`,
FFmpeg will trim the input audio stream, but here we just speed up the whole audio from 0, so we just skip over the trim
operation.

that is all of what `configure_input_audio_filter` does, in general, it will add abuffers based on how many inputs you specify
in your filter_complex string.

in our case, we have one input, and for now the total number of filters will be 2, one abuffer and one atempo.

## configure_output_audio_filter

next we will go to the function `configure_output_audio_filter` to add an abuffersink filter, and an aformat filter.

allocate and insert an abuffersink to the graph.

```c

    ret = avfilter_graph_create_filter(&ofilter->filter,
                                       avfilter_get_by_name("abuffersink"),
                                       name, NULL, NULL, fg->graph);
```

notice that this time, FFmpeg will pass `NULL` as the `arg` to the function `avfilter_graph_create_filter`, so there will be no
options for the abuffersink filter, no sample format, no sample rate, no layout.

then look up the sample format, the sample rates, the channel layout for the output file.

```c
    sample_fmts     = choose_sample_fmts(ofilter);
    sample_rates    = choose_sample_rates(ofilter);
    channel_layouts = choose_channel_layouts(ofilter);
```

what's important to note is that here `ofilter` is not a real filter instance that is an instance of `AVFilterContext` class,
`ofilter` is actually an instance of `OutputFilter` class, which has a `AVFilterContext` inside.

and `choose_sample_fmts` is defined as a macro function, and here let's just expand that marco out and make it better in terms
of reading.

```c
static char *choose_sample_fmts (OutputFilter *ofilter)                        
{                                                                      
    if (ofilter->format != AV_SAMPLE_FMT_NONE) {                                             
        GET_SAMPLE_FMT_NAME(ofilter->format);                                           
        return av_strdup(name);                                             
    } else if (ofilter->formats) {                              
        const AVSampleFormat *p;                                                         
        AVIOContext *s = NULL;                                                 
        uint8_t *ret;                                                          
        int len;                                                               
                                                                               
        if (avio_open_dyn_buf(&s) < 0)                                         
            exit_program(1);                                                           
                                                                               
        for (p = ofilter->formats; *p != AV_SAMPLE_FMT_NONE; p++) {                   
            GET_SAMPLE_FMT_NAME(*p);                                                      
            avio_printf(s, "%s|", name);                                       
        }                                                                      
        len = avio_close_dyn_buf(s, &ret);                                     
        ret[len - 1] = 0;                                                      
        return ret;                                                            
    } else                                                                     
        return NULL;                                                           
}
```

basically what `choose_sample_fmts` does is first to check if the `ofilter` has a format defined, if no, then fetch all the
formats stored in the array `ofilter->formats`, and join all of them to a string and return.

and the `ofilter` will copy the info from the encoder for the newly created output stream when parsing your encoder options.
this will happen in the function `open_output_file`.

```c
// ffmpeg_opt.c
static int open_output_file(OptionsContext *o, const char *filename)
{
        if (ost->filter) {
            OutputFilter *f = ost->filter;
            int count;
            switch (ost->enc_ctx->codec_type) {
            case AVMEDIA_TYPE_VIDEO:
            case AVMEDIA_TYPE_AUDIO:
                if (ost->enc_ctx->sample_fmt != AV_SAMPLE_FMT_NONE) {
                    f->format = ost->enc_ctx->sample_fmt;
                } else if (ost->enc->sample_fmts) {
                    count = 0;
                    while (ost->enc->sample_fmts[count] != AV_SAMPLE_FMT_NONE)
                        count++;
                    f->formats = av_mallocz_array(count + 1, sizeof(*f->formats));
                    if (!f->formats)
                        exit_program(1);
                    memcpy(f->formats, ost->enc->sample_fmts, (count + 1) * sizeof(*f->formats));
                }
                if (ost->enc_ctx->sample_rate) {
                    f->sample_rate = ost->enc_ctx->sample_rate;
                } else if (ost->enc->supported_samplerates) {
                    count = 0;
                    while (ost->enc->supported_samplerates[count])
                        count++;
                    f->sample_rates = av_mallocz_array(count + 1, sizeof(*f->sample_rates));
                    if (!f->sample_rates)
                        exit_program(1);
                    memcpy(f->sample_rates, ost->enc->supported_samplerates,
                           (count + 1) * sizeof(*f->sample_rates));
                }
        }
}
```

put simply, the `ofilter` contains the meta of the output file.

but the `ofilter` will finally be synced with the params for the frames that the graph throws out, we will see how later.

here `sample_fmts` will be FLTP, which the default audio format, and it is also the format the AAC encoder supports, which is
the default encoder used for audio encodnig.

as you can see, if you had specified options for your audio encoder, then those options would be stored in `enc_ctx`, otherwise,
FFmpeg will get the default options from `ost->enc`.

and the default `sample_fmts` in AAC encoder is going to be

```c
AVCodec ff_aac_encoder = {
    .name           = "aac",
    .long_name      = NULL_IF_CONFIG_SMALL("AAC (Advanced Audio Coding)"),
    .type           = AVMEDIA_TYPE_AUDIO,
    .id             = AV_CODEC_ID_AAC,
    .priv_data_size = sizeof(AACEncContext),
    .supported_samplerates = mpeg4audio_sample_rates,
    .sample_fmts    = (const enum AVSampleFormat[]){ AV_SAMPLE_FMT_FLTP,
                                                     AV_SAMPLE_FMT_NONE },
};
```

and the `supported_samplerates` is defined as

```c
static const int mpeg4audio_sample_rates[16] = {
    96000, 88200, 64000, 48000, 44100, 32000,
    24000, 22050, 16000, 12000, 11025, 8000, 7350
};
```

and now let's go back to `configure_output_audio_filter`.

if any of these three variable, `sample_fmts`, `sample_rates`, and `channel_layouts`, is set, FFmpeg will insert an aformat before
the abuffersink.

```c
    if (sample_fmts || sample_rates || channel_layouts) {
        AVFilterContext *format;
        ret = avfilter_graph_create_filter(&format,
                                           avfilter_get_by_name("aformat"),
                                           name, args, NULL, fg->graph);
        if (ret < 0)
            return ret;
        // here last_filter is the atempo.
        ret = avfilter_link(last_filter, pad_idx, format, 0);
        if (ret < 0)
            return ret;
    }
```

and why this aformat filter is needed?

in summary and in short, the output format from the last filter before abuffersink might not be the default audio format in
FFmpeg.

e.g. atempo actually gives out a format of FLT, but the default audio format is FLTP, then FFmpeg just want to
transformt the FLT to FLTP, and more details in section `graph_config_formats`.

**tips: if you run an atempo using PyAV, then you will get the output frame with FLT format.**

and even if the last filter outputs a format of FLTP, FFmpeg will add an aformat filter anyway since it just checks if that
`sample_formats` is being set, and does not compare and check if that is the default audio format.

and the last step, FFmpeg links the aformat to the abuffersink.

```c
    // this time last_fitler will be the aformat.
    if ((ret = avfilter_link(last_filter, pad_idx, ofilter->filter, 0)) < 0)
        return ret;

    return 0;
```

now we have 4 filters in our graph, an abuffer, an atempo, an aformat, and an abuffersink, there's still two filters missing,
the aresample prior to the atempo, and the aresample that comes after the atempo.

## avfilter_graph_config

next, `configure_filtergraph` will call `avfilter_graph_config` to really configure the graph.

```c
int avfilter_graph_config(AVFilterGraph *graphctx, void *log_ctx)
{
    int ret;

    if ((ret = graph_check_validity(graphctx, log_ctx)))
        return ret;
    if ((ret = graph_config_formats(graphctx, log_ctx)))
        return ret;
    if ((ret = graph_config_links(graphctx, log_ctx)))
        return ret;
    if ((ret = graph_check_links(graphctx, log_ctx)))
        return ret;
    if ((ret = graph_config_pointers(graphctx, log_ctx)))
        return ret;

    return 0;
}
```

we will force on `graph_config_formats` and `graph_config_links`.

## graph_config_formats

what `graph_config_formats` does is basically to query the formats of every filter supports, and determine the format of
every two adjacent filters.

first let's see how many formats for which atempo supports.

below is the structure of the atempo.

```c
AVFilter ff_af_atempo = {
    .name            = "atempo",
    .description     = NULL_IF_CONFIG_SMALL("Adjust audio tempo."),
    .init            = init,
    .uninit          = uninit,
    .query_formats   = query_formats,
    .process_command = process_command,
    .priv_size       = sizeof(ATempoContext),
    .priv_class      = &atempo_class,
    .inputs          = atempo_inputs,
    .outputs         = atempo_outputs,
};
```

the `query_formats` attribute points to the function that will be used for querying the formats that atempo supports.

```c
// af_atempo.c
static int query_formats(AVFilterContext *ctx)
{
    AVFilterChannelLayouts *layouts = NULL;
    AVFilterFormats        *formats = NULL;

    // WSOLA necessitates an internal sliding window ring buffer
    // for incoming audio stream.
    //
    // Planar sample formats are too cumbersome to store in a ring buffer,
    // therefore planar sample formats are not supported.
    //
    static const enum AVSampleFormat sample_fmts[] = {
        AV_SAMPLE_FMT_U8,
        AV_SAMPLE_FMT_S16,
        AV_SAMPLE_FMT_S32,
        AV_SAMPLE_FMT_FLT,
        AV_SAMPLE_FMT_DBL,
        AV_SAMPLE_FMT_NONE
    };
    formats = ff_make_format_list(sample_fmts);
    ret = ff_set_common_formats(ctx, formats);
    if (ret < 0)
        return ret;
}
```

above shows that atempo supports 5 formats for both ingress and egree, which means that the frames that are passed to an atempo
have to be any format of those 5 formats, and atempo will output frames with the same format as the input frames.

how? please see the section `audio sampling`.

variable `formats` in the code snippet is a `AVFilterFormats` structure.

```c
struct AVFilterFormats {
    unsigned nb_formats;        ///< number of formats
    int *formats;               ///< list of media formats

};
```

`nb_formats` indicates the number of formats, and `formats` is an integer array, and to query all the formats that a filter
supports, traverse through the `formats` array, and stop when you meet `AV_SAMPLE_FMT_NONE`.

`AVFilterContext->inputs[0]->outcfg->formats` is type of `AVFilterFormats`, and stores the input optional formats for the
filter.

`AVFilterContext->output[0]->incfg->formats` is type of `AVFilterFormats`, and stores the output optional formats for the
filter.

and in some case, they are same, and in other cases, they are not.

you can see that the `ctx->inputs[0]->outcfg->formats` and `ctx->output[0]->incfg->formats` are both set and store all of 5
formats in code snippet.

but what the incfg and the outcfg really are?

and for abuffer, we know that it will output frames of FLTP type, then the types don't match for the abuffer and the atemp
in our graph.

and an obvious and straightforward way to deal with this is resample frames, because FLT and FLTP can not be merged.

this is why FFmpeg will add an aresample filter in between them, we will talk about it later.

and aformat supports only one format, which is FLTP, and for abuffersink, it supports all of 12 audio formats.

actually there's no default formats for abuffersink in its query_formats function, and if no formats for a filter, FFmpeg
will pretend that it supports all the 12 audio formats.

how? 

the invoking chain is going to be:

```
configure_filtergraph -> graph_config_formats -> query_formats -> filter_query_formats
```

in `query_formats`, it will traverse all the filters, and check if one has set up a `query_formats` function in its structure.

if that filter does, then call its `query_formats` to query all the formats it supports, or call `ff_default_query_formats`.

```c
static int query_formats(AVFilterGraph *graph, AVClass *log_ctx)
{

    for (i = 0; i < graph->nb_filters; i++) {
        AVFilterContext *f = graph->filters[i];
        if (formats_declared(f))
            continue;
        if (f->filter->query_formats)
            ret = filter_query_formats(f);
        else
            ret = ff_default_query_formats(f);
        if (ret < 0 && ret != AVERROR(EAGAIN))
            return ret;
        /* note: EAGAIN could indicate a partial success, not counted yet */
        count_queried += ret >= 0;
    }
```

and in `filter_query_formats`, it calls the `query_formats` for a filter, if no formats for that filter, add all 12 audio
formats to ctx.

```c

    // call the query_formats function that the filter has in it.
    if ((ret = ctx->filter->query_formats(ctx)) < 0) {
        if (ret != AVERROR(EAGAIN))
            av_log(ctx, AV_LOG_ERROR, "Query format failed for '%s': %s\n",
                   ctx->name, av_err2str(ret));
        return ret;
    }

    //  here fetch all 12 formats !!!!!!!
    formats = ff_all_formats(type);
    // then add them into the ctx in case ctx has no formats. !!!!!!!!!!!
    if ((ret = ff_set_common_formats(ctx, formats)) < 0)
        return ret;
```

next FFmpeg will settle the format for every adjacent filters, and it also happens in function `query_formats`.

the approach the FFmpeg uses to determine the format is simple, if formats at either end for a link can be merged, then
the merged format will be the format, otherwise, add an aresample between.

```c
static int query_formats(AVFilterGraph *graph, AVClass *log_ctx)
{
    /* go through and merge as many format lists as possible */
    for (i = 0; i < graph->nb_filters; i++) {
        AVFilterContext *filter = graph->filters[i];

        for (j = 0; j < filter->nb_inputs; j++) {
            AVFilterLink *link = filter->inputs[j];
            int convert_needed = 0;

            if (!link)
                continue;

            // the formats are not equal!!!!!!!!!!!!
            if (link->incfg.formats != link->outcfg.formats
                && link->incfg.formats && link->outcfg.formats)
                if (!ff_can_merge_formats(link->incfg.formats, link->outcfg.formats,
                                          link->type))
                    convert_needed = 1;
            // and for a audio link, FFmpeg will check if they have the same samplerates as well.
            if (link->type == AVMEDIA_TYPE_AUDIO) {
                if (link->incfg.samplerates != link->outcfg.samplerates
                    && link->incfg.samplerates && link->outcfg.samplerates)
                    if (!ff_can_merge_samplerates(link->incfg.samplerates,
                                                  link->outcfg.samplerates))
                        convert_needed = 1;
            }
}
```

for a link of two adjacent filters, if the formats on either side are different, and `ff_can_merge_formats` returns that those
types can not be merged, then the flag `convert_needed` will be set to be 1.

below the diagram shows the filters, the links, and formats in our graph.

```

1/8 indicates that the filter supports 1 format and the first format in the array is number 8.

       1/8     5/0         5/0        1/8        1/8        12/0
abuffer --------->   atempo ------------> aformat -------------> abuffersink
          link A               link B                   link C
```

for FLTP and FLT, they are not mergable.

for link A, the abuffer spits out frames with a format of FLTP, and the atempo can not accept them, so the only way is going to
be adding an aresample filter.

```c
    if (convert_needed) {
        AVFilterContext *convert;
        switch (link->type) {
            case AVMEDIA_TYPE_AUDIO:
        
                snprintf(inst_name, sizeof(inst_name), "auto_resampler_%d",
                         resampler_count++);
                if ((ret = avfilter_graph_create_filter(&convert, filter,
                                                        inst_name, graph->aresample_swr_opts,
                                                        NULL, graph)) < 0)
                    return ret;
                break;

            // here link tha abuffer to the aresample, and link the aresample to atempo!!!!!!!!!!
            if ((ret = avfilter_insert_filter(link, convert, 0, 0)) < 0)
                return ret;
            // query the aresample's formats
            if ((ret = filter_query_formats(convert)) < 0)
                return ret;
        }
    }
```

then the graph will look like

```

       1/8      1/8              5/0       5/0        5/0     5/0              1/8   1/8        1/8     1/8
abuffer -----------> aresample_0 ------------> atempo ----------> aresample_1 ---------> aformat ----------> abuffersink

```

aresamples will output frames with the same format as the filter right next to them. 

## pick_formats

in our case, it's very easy to determine the format for some links, since the foramts on either side of each of those links are
an array of size 1, meaning that only one format for either end.

and for the linkage from the aresample_0 to the atempo and the linkage from the atempo to the aresample_1, we have to compute
the proper format for these two links.

in other words, the format `AV_SAMPLE_FMT_U8` whose number is 0 may not be the best format for the links.

`swap_sample_fmts` comes to help, the invoking chain is as follows:

```
configure_filtergraph -> avfilter_graph_config -> graph_config_formats -> swap_sample_fmts -> swap_sample_fmts_on_filter
```

after some kind of calculation, FFmpeg will move up the most-wanted format to the top of the array, and the graph will be

```

       1/8      1/8              5/3       5/3        5/3     5/3              1/8   1/8        1/8     1/8
abuffer -----------> aresample_0 ------------> atempo ----------> aresample_1 ---------> aformat ----------> abuffersink

```

the atempo will accept FLT as the input format, and output a format of FLT as well.

finally, make the decision.

and then `graph_config_formats` will call the function `pick_formats` that is responsible for picking up the right format
for each link and assign the format to `link->format`.

the invoking chain is

```
configure_filtergraph -> avfilter_graph_config -> graph_config_formats -> pick_formats -> pick_format
```

and the best format for a link is computed based on scores, and smaller score, and best format.

```c

static int pick_format(AVFilterLink *link, AVFilterLink *ref)
{
    if (!link || !link->incfg.formats)
        return 0;

    if (link->type == AVMEDIA_TYPE_VIDEO) {
    } else if (link->type == AVMEDIA_TYPE_AUDIO) {
        if(ref && ref->type == AVMEDIA_TYPE_AUDIO){
            enum AVSampleFormat best= AV_SAMPLE_FMT_NONE;
            int i;
            for (i = 0; i < link->incfg.formats->nb_formats; i++) {
                enum AVSampleFormat p = link->incfg.formats->formats[i];
                best = find_best_sample_fmt_of_2(best, p, ref->format);
            }
            link->incfg.formats->formats[0] = best;
        }
    }
```

as you can see, the `link` will point to `aresample_0 -----> atempo`, `ref` pints to the link `abuffer --> aresample_0`.

as we know, `ref` will have a format of FLTP, which is stored as `ref->format`, and then we have to find the best format to
`ref->format`.

and `link->incfg.formats->nb_formats` will be 5, and `find_best_sample_fmt_of_2` will find the best format to `ref-format` for us.

```c
static enum AVSampleFormat find_best_sample_fmt_of_2(enum AVSampleFormat dst_fmt1, enum AVSampleFormat dst_fmt2,
                                                     enum AVSampleFormat src_fmt)
{
    int score1, score2;

    score1 = get_fmt_score(dst_fmt1, src_fmt);
    score2 = get_fmt_score(dst_fmt2, src_fmt);

    return score1 < score2 ? dst_fmt1 : dst_fmt2;
}
```

here `score1` would be 401, and `score2` would be 1, then if `score1` is smaller than `score2`, return `dst_fmt1`, which is
`AV_SAMPLE_FMT_NONE`, else return `dst_fmt2`, which is `AV_SAMPLE_FMT_FLT`.

so in the first round of the iteration, the best format is going to be swapped to FLT, and then next, continue to find the
best among the rest of formats, compared to FLT.

and it turns out that the FLT is the best!(FLT has a score of 1, that is a very small number)

after all, the graph will become:

```
          FLTP                FLT           FLT                FLTP             FLTP
abuffer ------> aresample_0 ------> atempo -----> aresample_1 -------> aformat ------> abuffersink

```

## graph_config_links

here FFmpeg will choose the `time_base` and the `frame_rate` for each link and configure their prive data.

and it runs from back to front to configure every link.

```c
static int graph_config_links(AVFilterGraph *graph, AVClass *log_ctx)
{
    AVFilterContext *filt;
    int i, ret;

    for (i = 0; i < graph->nb_filters; i++) {
        filt = graph->filters[i];

        if (!filt->nb_outputs) {
            if ((ret = avfilter_config_links(filt)))
                return ret;
        }
    }

    return 0;
}
```

the first and the only filter that gets passed into the function `avfilter_config_links` is going to be the abuffersink, because
it's the only one who has no outputs.

`avfilter_config_links` simply traverses the filters starting from the abuffersink, and visits the input link of that filter,
and sets up time_base and frame_rate for the link.

```c
int avfilter_config_links(AVFilterContext *filter)
{
    int (*config_link)(AVFilterLink *);
    unsigned i;
    int ret;

    for (i = 0; i < filter->nb_inputs; i ++) {
        AVFilterLink *link = filter->inputs[i];
        switch (link->init_state) {
        case AVLINK_INIT:
            continue;
        case AVLINK_STARTINIT:
            av_log(filter, AV_LOG_INFO, "circular filter chain detected\n");
            return 0;
        case AVLINK_UNINIT:
            link->init_state = AVLINK_STARTINIT;

            if ((ret = avfilter_config_links(link->src)) < 0)
                return ret;

            if (!(config_link = link->srcpad->config_props)) {
                if (link->src->nb_inputs != 1) {
                    av_log(link->src, AV_LOG_ERROR, "Source filters and filters "
                                                    "with more than one input "
                                                    "must set config_props() "
                                                    "callbacks on all outputs\n");
                    return AVERROR(EINVAL);
                }
            } else if ((ret = config_link(link)) < 0) {
                av_log(link->src, AV_LOG_ERROR,
                       "Failed to configure output pad on %s\n",
                       link->src->name);
                return ret;
            }
    }
}
```

there are three states for a link, `AVLINK_INIT`, `AVLINK_STARTINIT`, and `AVLINK_UNINIT`.

if a link is now in the state of `AVLINK_INIT`, then it has been configured, nothing to do.

if a link is `AVLINK_STARTINIT` and it now gets visited twice, then a circular linkage detected, error.

if a link is `AVLINK_UNINIT`, turn the knob to change its state as `AVLINK_STARTINIT`, run the configuration.

and for a link, it will first call `avfilter_config_links` to configure its source recursively.

```

the number shows the order of a link being configured. 

           4                        3              2                        1                 0
  abuffer ----------> aresample_0 --------> atempo ----------> aresample_0 --------> aformat ------> abuffsink 
           link A                  link B           link C                  link D            link E
```

to configure a link, first, call the function that is defined on `link->srcpad->config_props`.

for simplicity, `link->srcpad->config_props` is the function that must be called when a filter is locating at the source of a link.

e.g. abuffer has its `config_props`, when an abuffer is placed at the source, you have to call that function to initialize the
private data of that abuffer filter.


```c
static int config_props(AVFilterLink *link)
{
    BufferSourceContext *c = link->src->priv;

    switch (link->type) {
    case AVMEDIA_TYPE_AUDIO:
        if (!c->channel_layout)
            c->channel_layout = link->channel_layout;
        break;
    default:
        return AVERROR(EINVAL);
    }

    link->time_base = c->time_base;
    link->frame_rate = c->frame_rate;
    return 0;
}
```

the time_base and the frame_rate of the link A will be the ones in the private data of the abuffer filter.

and let's recall that the abuffer was created using a string of `"time_base=1/44100:sample_rate=44100:sample_fmt=fltp:channel_layout=0x3"`.

then the time_base for the abuffer is going to be 44100, and the frame_rate remains 0 since this is an audio filter.

and then if the link has no time_base, then FFmpeg will take the time_base from the previous link and assign it to the link.

```c
            case AVMEDIA_TYPE_AUDIO:
                if (inlink) {
                    if (!link->time_base.num && !link->time_base.den)
                        link->time_base = inlink->time_base;
                }

                if (!link->time_base.num && !link->time_base.den)
                    link->time_base = (AVRational) {1, link->sample_rate};
            }
```

inink is defined as 

```c
inlink = link->src->nb_inputs ? link->src->inputs[0] : NULL;
```

basically, link A is the `inlink` to the link B, and so on.

last, call the `config_prop` in the dst filter of the link.

```c
            if ((config_link = link->dstpad->config_props))
                if ((ret = config_link(link)) < 0) {
                    av_log(link->dst, AV_LOG_ERROR,
                           "Failed to configure input pad on %s\n",
                           link->dst->name);
                    return ret;
                }

            link->init_state = AVLINK_INIT;
```

for link A, the dst filter is aresample_0, and it has no `config_prop`, which means that when an aresample filter is at the end
of the link, nothing to configure, but when it sits at the source of the link, it has to configure its sample context.

and then the last step, mark the link as `AVLINK_INIT`.

## sync the ofilter

after finishing `avfilter_graph_config`, `ofilter` will copy the settings from sink filter to it.

```c
    if ((ret = avfilter_graph_config(fg->graph, NULL)) < 0)
        goto fail;
    for (i = 0; i < fg->nb_outputs; i++) {
        OutputFilter *ofilter = fg->outputs[i];
        AVFilterContext *sink = ofilter->filter;

        ofilter->format = av_buffersink_get_format(sink);

        ofilter->width  = av_buffersink_get_w(sink);
        ofilter->height = av_buffersink_get_h(sink);

        ofilter->sample_rate    = av_buffersink_get_sample_rate(sink);
        ofilter->channel_layout = av_buffersink_get_channel_layout(sink);
    }
```

that says that the format, the width, the height, and all other attributes that are used by the encoder are the attributes
that the graph assigns for the frames at the end.

# Initialization summary

```

configure_filtergraph
  - configure_input_audio_filter,  add an abuffer.
  - configure_output_audio_filter, add an abffersink and an aformat.
  - avfilter_graph_config
    - graph_config_formats
      - query_formats, query formats and add aresamples into the graph.
      - pick_formats,  set up the format for each link.
    - graph_config_links, configure links, including seting up time_base and frame_rate.

```

# graph.configure in PyAV

the method `graph.configure` is acutally pointing to the function `avfilter_graph_config`.

according to the summary, you have to insert abuffer and abuffersink yourself, and you won't have that aformat in your graph. 

but you will still have those two aresample filters on both side of the atempo.

# Audio sampling

we just leave aside how a graph runs in details, for more inforation, please see `graph_execution.md`.

running the graph to filter frames, and afterwards, FFmpeg will sample the frames out of the graph before sending to the encoder.

FFmpeg has a different process for audio and video stream, here let's see what happens to the audio stream.

**in a nutshell, FFmpeg will wait until the number of audio samples reaching a particular value, then combine the certain amount
of audio samples into a frame, then send that frame to the encoder.**

and the function `reap_filters` is the one who does the sampling.

## Copying audio samples

FFmpeg will continually pull and consume frames out of the graph in a while loop.

```c

        while (1) {
            ret = av_buffersink_get_frame_flags(filter, filtered_frame,
                                               AV_BUFFERSINK_FLAG_NO_REQUEST);
        }

```

and the invoking chain is like

```
av_buffersink_get_frame_flags -> get_frame_internal -> ff_inlink_consume_samples
```

the function `get_frame_interal` will consume audio samples or return video frame as you want. 

```c
    while (1) {
        ret = samples ? ff_inlink_consume_samples(inlink, samples, samples, &cur_frame) :
                        ff_inlink_consume_frame(inlink, &cur_frame);
```

if you want to get certain amount of audio samples back, just pass into a parameter `samples` that is not zero.

the value of variable `samples` is determined by your encoder, and we will talk about it later, here `samples` is 1024.

and `ff_inlink_consume_samples` will first check if there are enough samples stored in the queue of the link that points to
the abuffersink.

```
aformat ------------------------> abuffersink
          queue: frames/samples
``` 

and if it does, copy 1024 samples to a new frame, and adjust the number of samples remaining in the queue, and return the frame.

```c

static inline uint64_t ff_framequeue_queued_samples(const FFFrameQueue *fq)
{
    return fq->total_samples_head - fq->total_samples_tail;
}

int ff_inlink_check_available_samples(AVFilterLink *link, unsigned min)
{
    uint64_t samples = ff_framequeue_queued_samples(&link->fifo);
    av_assert1(min);
    return samples >= min || (link->status_in && samples);
}

int ff_inlink_consume_samples(AVFilterLink *link, unsigned min, unsigned max,
                            AVFrame **rframe)
{
    AVFrame *frame;
    int ret;

    av_assert1(min);
    *rframe = NULL;
    if (!ff_inlink_check_available_samples(link, min))
        return 0;
    if (link->status_in)
        min = FFMIN(min, ff_framequeue_queued_samples(&link->fifo));
    ret = take_samples(link, min, max, &frame);
    if (ret < 0)
        return ret;
    consume_update(link, frame);
    *rframe = frame;
    return 1;
}
```

the function `take_samples` will take the specified amount of samples out to fill in the frame.

## take_samples

`take_samples` will keep taking frames in the queue from head to tail until the amount of samples is equal to or greater than
1024.

for instance, suppose there are 4 frames in the queue, and the size of each is going to be:

```
frame1(300), frame2(512), frame3(400), frame4(100)
```

then FFmpeg will iterate the queue to count how many frames it should take at first.

in our case, it should take the first 2 frames because if you take the first 3 frames, then the amount of samples is going to
be greater than 1024.

and then FFmpeg will pop the frame1 and frame2 from the queue, and it finds out that the accumulated amount is still
less than 1024, so it will go take a portion of the third frame to have enough samples.

it will extract 1024 - (300 + 512) = 212 samples from the third frame, and append them into the newly created frame.

let's see how this is done in code.

```c
    frame0 = frame = ff_framequeue_peek(&link->fifo, 0);
    nb_frames = 0;
    nb_samples = 0;
    while (1) {
        if (nb_samples + frame->nb_samples > max) {
            if (nb_samples < min)
                nb_samples = max;
            break;
        }
        nb_samples += frame->nb_samples;
        nb_frames++;
        if (nb_frames == ff_framequeue_queued_frames(&link->fifo))
            break;
        frame = ff_framequeue_peek(&link->fifo, nb_frames);
    }
```

`nb_frames` indicates that the first N frames FFmpeg should take, and `nb_samples` is the total amount of samples it has had
so far.

`·ff_framequeue_peek` returns the reference of the frame at ith index, so at the end of that while loop, FFmpeg will get the
frame at the next index.

so far, FFmpeg has not popped any frame, it just calculates minimum the number of frames it should take.

and next, pop the frames, and chop off the first X samples from the frame at the head of the queue.

```c
    buf->pts = frame0->pts;
    p = 0;
    for (i = 0; i < nb_frames; i++) {
        frame = ff_framequeue_take(&link->fifo);
        av_samples_copy(buf->extended_data, frame->extended_data, p, 0,
                        frame->nb_samples, link->channels, link->format);
        p += frame->nb_samples;
        av_frame_free(&frame);
    }
    if (p < nb_samples) {
        unsigned n = nb_samples - p;
        frame = ff_framequeue_peek(&link->fifo, 0);
        av_samples_copy(buf->extended_data, frame->extended_data, p, 0, n,
                        link->channels, link->format);
        ff_framequeue_skip_samples(&link->fifo, n, link->time_base);
    }
    *rframe = buf;
```

`ff_framequeue_take` will really pop the frame out of the queue, and copy samples into the buffer by calling `av_samples_copy`.

if p, which represents the total number of samples that FFmpeg has copied, is less than 1024, then visit the head of the queue,
take out the first N samples, and shirnk it, and adjust the pointers.

so everytime, `take_samples` will take out 1024 sample, but here is a problem, suppose we slow down an audio stream by 2 times,
then atempo will output 2048 samples for each frame, then you will find that the total amount of samples in the queue will keep
increasing, and you are going to have memory leak!

so this is why FFmpeg take samples in a while loop in the function `reap_filters`, it will take as many samples as possible
until the amount of samples in the queue is less than 1024.

if FFmpeg meets an error of EAGAIN, meaning no more avaliable samples, just break the loop.

```c

        while (1) {
            ret = av_buffersink_get_frame_flags(filter, filtered_frame,
                                               AV_BUFFERSINK_FLAG_NO_REQUEST);
            if (ret < 0) {
                if (ret != AVERROR(EAGAIN) && ret != AVERROR_EOF) {
                    av_log(NULL, AV_LOG_WARNING,
                           "Error in av_buffersink_get_frame_flags(): %s\n", av_err2str(ret));
                } else if (flush && ret == AVERROR_EOF) {
                    if (av_buffersink_get_type(filter) == AVMEDIA_TYPE_VIDEO)
                        do_video_out(of, ost, NULL);
                }
                break;
            }
```

## pts for the frame

and another every important thing here is that the pts of the frame is going to be pts of the first frame in the queue.

```c
buf->pts = frame0->pts;
```

since every frame will be size of 1024, then obviously, the pts sequence will be a sequence of 1024 times N, where N is
integer and starts from 0.

```
0, 1024, 2048, 3072, ...., 1024*N, ...
```

and of course, `ff_framequeue_skip_samples` will adjust the pts of the frame after taking out a portion of it.

```c
    if (b->frame->pts != AV_NOPTS_VALUE)
        b->frame->pts += av_rescale_q(samples, av_make_q(1, b->frame->sample_rate), time_base);
```

as you can see, `b->frame` is the frame, and its pts will be increased by samples if the `time_base` is the reciprocal of the
`b->frame->sample_rate`.

we will explain what `av_rescale_q` does in the section `speed up the video track`, here we just assume that `av_rescale_q`
returns `samples` that you pass in back.

assume we slow down the audio stream by 2.2 times, and then everytime atempo will output 465 samples, and we need to take 
1024-465x2=94 samples from the head of the queue.

then `b->frame->pts` is 930 first, and `samples` is 94, then `b->frame->pts` will be changed to be 930+94=1024.


## frame_size, the amount of smaples

how many samples should FFmpeg take out of the queue? it depends on your encoder.

```c
get_frame_internal(ctx, frame, flags, ctx->inputs[0]->min_samples);
```

as we can see, `min_samples` in `ctx->inputs[0]` stores the number of samples.

`ctx->inputs[0]` is the link that points to the abuffersink.

```
aformat ---------------> abuffersink
         min_samples
```

but when and how this `min_samples` gets determined?

it is when FFmpeg initialize the encoder context, the invoking chain is:

```
init_output_stream_wrapper -> init_output_stream -> avcodec_open2
                                                 -> av_buffersink_set_frame_size
```

as comments in `reap_filters` say, qoute, the audio frame size matters, unqoute.

```c
        /*
         * Unlike video, with audio the audio frame size matters.
         * omit some words....
         * Thus, if we have gotten to an audio stream, initialize
         * the encoder earlier than receiving the first AVFrame.
         */
        if (av_buffersink_get_type(filter) == AVMEDIA_TYPE_AUDIO)
            init_output_stream_wrapper(ost, NULL, 1);
```

and in `init_output_stream`, it will call `avcodec_open2` to initialize the encoder, and then `av_buffersink_set_frame_size`
will set up the min_sample as the frame_size of the encoder context.

```c
        if ((ret = avcodec_open2(ost->enc_ctx, codec, &ost->encoder_opts)) < 0) {
            if (ret == AVERROR_EXPERIMENTAL)
                abort_codec_experimental(codec, 1);
            snprintf(error, error_len,
                     "Error while opening encoder for output stream #%d:%d - "
                     "maybe incorrect parameters such as bit_rate, rate, width or height",
                    ost->file_index, ost->index);
            return ret;
        }
        if (ost->enc->type == AVMEDIA_TYPE_AUDIO &&
            !(ost->enc->capabilities & AV_CODEC_CAP_VARIABLE_FRAME_SIZE))
            av_buffersink_set_frame_size(ost->filter->filter,
                                            ost->enc_ctx->frame_size);
```

`avcodec_open2` will call the init function of the certain encoder.

```c
    // avcodec.c:351
    if (   avctx->codec->init && (!(avctx->active_thread_type&FF_THREAD_FRAME)
        || avci->frame_thread_encoder)) {
        // here !!!!!!!!!!!!!!!!!
        ret = avctx->codec->init(avctx);
        if (ret < 0) {
            codec_init_ok = -1;
            goto free_and_end;
        }
        codec_init_ok = 1;
    }
```

let's take AAC encoder as an example, the default frame_size of AAC encoder is going to be 1024.

```c
static av_cold int aac_encode_init(AVCodecContext *avctx)
{
    AACEncContext *s = avctx->priv_data;
    int i, ret = 0;
    const uint8_t *sizes[2];
    uint8_t grouping[AAC_MAX_CHANNELS];
    int lengths[2];

    /* Constants */
    s->last_frame_pb_count = 0;
    avctx->frame_size = 1024;
    avctx->initial_padding = 1024;
```

and next, `av_buffersink_set_frame_size` will access the frame_size of the encoder context.

```c
void av_buffersink_set_frame_size(AVFilterContext *ctx, unsigned frame_size)
{
    AVFilterLink *inlink = ctx->inputs[0];
    // !!!!!!!!!!!!!!!!!!
    inlink->min_samples = inlink->max_samples =
    inlink->partial_buf_size = frame_size;
}
```

# samples and pts in atempo

how atempo works? we do not want to talk about the algorithm implementation, we just want to explain how atempo compute
the pts sequence.

first calculate the samples that it will output.

```c
// af_atempo.c:1079
static int filter_frame(AVFilterLink *inlink, AVFrame *src_buffer)
{
    int n_in = src_buffer->nb_samples;
    int n_out = (int)(0.5 + ((double)n_in) / atempo->tempo);
}
```

`atempo->tempo` is the value that you specify for the atempo filter, if your expression for atempo is `atempo=2.0`, then
`atempo->tempo` will be 2.0.

`n_in` is the number of samples that the input frame contains, in our case, it's 1024.

so `n_out` is going to be 512=1024/2, if we slow down the audio stream by 2.2 times, then `n_out` is going to be 1024/2.2 = 465,
and so on.

but it doesn't mean that for very frame that gets passed in, atempo will always output 512 samples.

no, sometime atempo will output 0 samples for an input frame, sometimes there's N samples out by the algorithm it uses.

what that 512 means is that atempo will wait until the amount of samples it caches up to 512, then pack those 512 samples into
a frame, and send to the next filter.

```c
    while (src < src_end) {
        if (!atempo->dst_buffer) {
            atempo->dst_buffer = ff_get_audio_buffer(outlink, n_out);
            if (!atempo->dst_buffer) {
                av_frame_free(&src_buffer);
                return AVERROR(ENOMEM);
            }
            av_frame_copy_props(atempo->dst_buffer, src_buffer);

            atempo->dst = atempo->dst_buffer->data[0];
            atempo->dst_end = atempo->dst + n_out * atempo->stride;
        }

        yae_apply(atempo, &src, src_end, &atempo->dst, atempo->dst_end);

        if (atempo->dst == atempo->dst_end) {
            int n_samples = ((atempo->dst - atempo->dst_buffer->data[0]) /
                             atempo->stride);
            ret = push_samples(atempo, outlink, n_samples);
            if (ret < 0)
                goto end;
        }
    }

    atempo->nsamples_in += n_in;
```

above, `atempo->dst_buffer` is the cache that holds the number of output samples, and it will be initialized to a size of `n_out`.

`yae_apply` is where atempo really speeds up or slows down the audio frame using its own algorithm.

and the amount of samples that get pushed into the cache can be calculated by comparing `atempo->dst` and `atempo->dst_end`.

 `atempo->dst` indicates the head of the buffer, and `dst_end` is the end of the buffer, if these two address is
equal to each other, then the cache is full containing at least `n_out` number of samples.

if they are equal, then we have enough samples in cache, then notify the next filter by pushing the frame into the queue of
its output link, otherwise, just continue.

then `push_samples` will take out 512 samples and put them into a frame, and calculate the pts for the frame.

`ff_filter_frame` will enqueue the frame, and mark the next fitler as ready, how? see `graph_execution.md`.

```c
static int push_samples(ATempoContext *atempo,
                        AVFilterLink *outlink,
                        int n_out)
{
    int ret;

    atempo->dst_buffer->sample_rate = outlink->sample_rate;
    atempo->dst_buffer->nb_samples  = n_out;

    // adjust the PTS:
    atempo->dst_buffer->pts = atempo->start_pts +
        av_rescale_q(atempo->nsamples_out,
                     (AVRational){ 1, outlink->sample_rate },
                     outlink->time_base);

    ret = ff_filter_frame(outlink, atempo->dst_buffer);
    atempo->dst_buffer = NULL;
    atempo->dst        = NULL;
    atempo->dst_end    = NULL;
    if (ret < 0)
        return ret;

    atempo->nsamples_out += n_out;
    return 0;
}
```

as we can see, pts for the frame is equal to the start_pts plus how many samples that atempo has sent out.

so if `n_out` is 512, then the pts sequence of output frames is going to be `512*N`, and if `n_out` is 465, it's `465*N`. 

and at the end of the function, FFmpeg will reset `atempo->dst_buffer` as NULL, next time atempo filters a frame, it will
reallocate space for a new `dst_buffer`.

below the diagram shows the frams in atempo cache, and the frames that FFmpeg gets in `reap_filters`.

```

for symbols like (0, 465), it means that the frame has a pts of 0 and 465 samples in it. 

input samples    frames in atempo cache                        frames in reap_filters      
                
  0                                   
                
  1024                                
                
  2048                                
                
  3072              
                
  4096           (0,465),(465,465)     
                
  5120           (0,465),(465,465) 
                
  6144           (0,465),(465,465),(930,465),(1395,465)        (0,1024)

  7168           (1024,371),(1395,465),(1860,465),(2325,465)   (1024,1024)

```

# Speed up the video track

the command

```
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.5*PTS[v]" -map "[v]" -y output.mp4
```

after graph configuration, the graph will contain 4 filters in total.

```
buffer -> setpts -> format -> buffersink
```

## Video formats

there are up to 297 video formats that FFmpeg supports, and they are defined in a constant `AVPixelFormat`, which is
type of `enum`.

and in our case, the total number of video formats that FFmpeg supports by default is going to be 198.

and the first format in `AVPixelFormat` is `AV_PIX_FMT_YUV420P` whose numeric value is 0, which is the default video format.

but each encoder has its own format support list, e.g. libx264 supports 30 video formats at most, you can find them
at `libx264.c`.

## configure_input_video_filter

allocate memory for a buffer filter, and push it into the graph.

```c
static int configure_input_video_filter(FilterGraph *fg, InputFilter *ifilter,
                                        AVFilterInOut *in)
{
    const AVFilter *buffer_filt = avfilter_get_by_name("buffer");
    AVRational tb = ist->framerate.num ? av_inv_q(ist->framerate) :
                                     ist->st->time_base;
    av_bprintf(&args,
             "video_size=%dx%d:pix_fmt=%d:time_base=%d/%d:"
             "pixel_aspect=%d/%d",
             ifilter->width, ifilter->height, ifilter->format,
             tb.num, tb.den, sar.num, sar.den);
    if ((ret = avfilter_graph_create_filter(&ifilter->filter, buffer_filt, name,
                                        args.str, NULL, fg->graph)) < 0)
}
```

the string that is being used to initialize the buffer is going to be

```
"video_size=1280x720:pix_fmt=0:time_base=1/60000:pixel_aspect=0/1:frame_rate=30000/1001"
```

these options are coming from your input file, and stored in variable `ifilter` when FFmpeg parsing the input file.

and FFmpeg will also do autorotate, deinterlace, and trim if it has to, but in generic scene, those operations are skipped over.

and lastly, link the buffer to the setpts.

```c
    if ((ret = avfilter_link(last_filter, 0, in->filter_ctx, in->pad_idx)) < 0)
        return ret;
```

## configure_output_video_filter

similar to `configure_output_audio_filter`, here FFmpeg will insert a buffersink filter and a format filter into the graph.

```c
    ret = avfilter_graph_create_filter(&ofilter->filter,
                                       avfilter_get_by_name("buffersink"),
                                       name, NULL, NULL, fg->graph);
```

FFmpeg will leave the options string for the buffersink as NULL.

and next, add a format filter in between setpts and buffersink.

```c
    if ((pix_fmts = choose_pix_fmts(ofilter))) {
        AVFilterContext *filter;
        snprintf(name, sizeof(name), "format_out_%d_%d",
                 ost->file_index, ost->index);
        ret = avfilter_graph_create_filter(&filter,
                                           avfilter_get_by_name("format"),
                                           "format", pix_fmts, NULL, fg->graph);
        av_freep(&pix_fmts);
        if (ret < 0)
            return ret;
        if ((ret = avfilter_link(last_filter, pad_idx, filter, 0)) < 0)
            return ret;

        last_filter = filter;
        pad_idx     = 0;
    }
```


`choose_pix_fmts` actually reads the configurations from the output stream, and passing into ofilter just for the purpose of
accessing the output stream at the ofilter, and then getting the configurations for the output encoder.

so `choose_pix_fmts` will eventually return the formats that encoder supports, and the default video encoder in FFmpeg will
be libx264.

and libx264 supports 30 formats at most by default.

```c
static const enum AVPixelFormat pix_fmts_all[] = {
    AV_PIX_FMT_YUV420P,
    AV_PIX_FMT_YUVJ420P,
    AV_PIX_FMT_YUV422P,
    AV_PIX_FMT_YUVJ422P,
    AV_PIX_FMT_YUV444P,
    AV_PIX_FMT_YUVJ444P,
    AV_PIX_FMT_NV12,
    AV_PIX_FMT_NV16,
#ifdef X264_CSP_NV21
    AV_PIX_FMT_NV21,
#endif
    AV_PIX_FMT_YUV420P10,
    AV_PIX_FMT_YUV422P10,
    AV_PIX_FMT_YUV444P10,
    AV_PIX_FMT_NV20,
#ifdef X264_CSP_I400
    AV_PIX_FMT_GRAY8,
    AV_PIX_FMT_GRAY10,
#endif
    AV_PIX_FMT_NONE
};

AVCodec ff_libx264_encoder = {
    .name             = "libx264",
    .long_name        = NULL_IF_CONFIG_SMALL("libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10"),
    .type             = AVMEDIA_TYPE_VIDEO,
    .id               = AV_CODEC_ID_H264,
    .priv_data_size   = sizeof(X264Context),
    .init             = X264_init,
    .encode2          = X264_frame,
    .close            = X264_close,
    .capabilities     = AV_CODEC_CAP_DELAY | AV_CODEC_CAP_OTHER_THREADS |
                        AV_CODEC_CAP_ENCODER_REORDERED_OPAQUE,
    .caps_internal    = FF_CODEC_CAP_AUTO_THREADS,
    .priv_class       = &x264_class,
    .defaults         = x264_defaults,
#if X264_BUILD < 153
    .init_static_data = X264_init_static,
#else
    .pix_fmts         = pix_fmts_all,
#endif
    .caps_internal  = FF_CODEC_CAP_INIT_CLEANUP | FF_CODEC_CAP_AUTO_THREADS
#if X264_BUILD >= 158
                      | FF_CODEC_CAP_INIT_THREADSAFE
#endif
                      ,
    .wrapper_name     = "libx264",
};
```

note that so far, the codec context, which is the priviate data for the codec, has not been initialized, so the formats will not
be the ones that you specify for the code context, it will be the formats that the encoder supports by defualt.

```c
    // now ost->enc_ctx->pix_fmt is NONE !!!!!
    if (ost->enc_ctx->pix_fmt != AV_PIX_FMT_NONE) {
        return av_strdup(av_get_pix_fmt_name(choose_pixel_fmt(ost->st, ost->enc_ctx, ost->enc, ost->enc_ctx->pix_fmt)));
    } else if (ost->enc && ost->enc->pix_fmts) {
        const enum AVPixelFormat *p;
        AVIOContext *s = NULL;
        uint8_t *ret;
        int len;
        // get the default formats that the encoder supports !!!!!
        p = ost->enc->pix_fmts;
        // assemble those formats into a string !!!!!!
        for (; *p != AV_PIX_FMT_NONE; p++) {
            const char *name = av_get_pix_fmt_name(*p);
            avio_printf(s, "%s|", name);
        }
        len = avio_close_dyn_buf(s, &ret);
        ret[len - 1] = 0;
        return ret;
    } else
        return NULL;
```

as you can see, the formats string will be constructed from `ost->enc->pix_fmts`.

and then the variable `pix_fmts` will be a string like this

```
"yuv420p|yuvj420p|yuv422p|yuvj422p|yuv444p|yuvj444p|nv12|nv16|nv21|yuv420p10le|yuv422p10le|yuv444p10le|nv20le|gray|gray10le"
```

these are 15 formats that will be head over to format init function.

next, link the setpts to the format, and then to the buffersink.

## graph_config_formats

setpts supports all 198 formats, and buffer is created with a pix_fmt of YUV420P, and buffersink accepts all 198 formats, and
format supports 15 formats mentioned above.

after querying formats for each filter, the graph looks like,

```

       1/0      198/0         198/0    15/0          15/0    198/0
buffer --------------> setpts --------------> format --------------> buffersink

```

and after formats merging,

```

       1/0        1/0         1/0        1/0        1/0          1/0
buffer --------------> setpts --------------> format --------------> buffersink

```

then finally after `pick_formats`(`swap_sample_fmts` is for audio stream only), 

```

          YUV420P                  YUV420P             YUV420P
buffer --------------> setpts --------------> format --------------> buffersink

```

## graph_config_links

for buffer filter, `config_props` will copy the width, the height, the time_base, and the frame_rate that FFmpeg got in
buffer construction.

remember that string that starts with `video_size=1280x720`.

```c
static int config_props(AVFilterLink *link)
{
    BufferSourceContext *c = link->src->priv;

    switch (link->type) {
    case AVMEDIA_TYPE_VIDEO:
        link->w = c->w;
        link->h = c->h;
        link->sample_aspect_ratio = c->pixel_aspect;

        if (c->hw_frames_ctx) {
            link->hw_frames_ctx = av_buffer_ref(c->hw_frames_ctx);
            if (!link->hw_frames_ctx)
                return AVERROR(ENOMEM);
        }
        break;
    link->time_base = c->time_base;
    link->frame_rate = c->frame_rate;
    return 0;
}
```

and then for other filters, just call their `config_props` functions, `srcpad->config_props` for the `link->src` and
`dstpad->config_props` for the `link->dst`. 

## Take the video frame from the graph

similar to the audio stream, `reap_filters` will try to get the frame from the graph by `av_buffersink_get_frame_flags`.

but different from the audio stream, `av_buffersink_get_frame_flags` will call `ff_inlink_consume_frame` to pop the
frame at the head of the queue of the buffsink.

```c

int ff_inlink_check_available_frame(AVFilterLink *link)
{
    return ff_framequeue_queued_frames(&link->fifo) > 0;
}

int ff_inlink_consume_frame(AVFilterLink *link, AVFrame **rframe)
{
    AVFrame *frame;

    *rframe = NULL;
    if (!ff_inlink_check_available_frame(link))
        return 0;

    if (link->fifo.samples_skipped) {
        frame = ff_framequeue_peek(&link->fifo, 0);
        return ff_inlink_consume_samples(link, frame->nb_samples, frame->nb_samples, rframe);
    }

    frame = ff_framequeue_take(&link->fifo);
    consume_update(link, frame);
    *rframe = frame;
    return 1;
}
```

`ff_framequeue_queued_frames` returns the value of `link->fifo->queued`, which indicates the number of frames that have enqueued.

if there's any frame queued, then `ff_framequeue_take` will pop out the first frame in the queue, and decrement the value of
`link->fifo->queued` by one.

and then reap_filters will call `do_video_out` with that frame to do the sampling. 

## Calculating float_pts and frame.pts

the first thing to do is to calculate and adjust the pts of the frame, which happens in the function
`adjust_frame_pts_to_encoder_tb`.

let's take a look at the code snippet.

```c
AVFilterContext *filter = ost->filter->filter;

int64_t start_time = (of->start_time == AV_NOPTS_VALUE) ? 0 : of->start_time;
AVRational filter_tb = av_buffersink_get_time_base(filter);
AVRational tb = enc->time_base;
int extra_bits = av_clip(29 - av_log2(tb.den), 0, 16);

tb.den <<= extra_bits;
float_pts =
    av_rescale_q(frame->pts, filter_tb, tb) -
    av_rescale_q(start_time, AV_TIME_BASE_Q, tb);
float_pts /= 1 << extra_bits;
// avoid exact midoints to reduce the chance of rounding differences, this can be removed in case the fps code is changed to work with integers
float_pts += FFSIGN(float_pts) * 1.0 / (1<<17);

frame->pts =
    av_rescale_q(frame->pts, filter_tb, enc->time_base) -
    av_rescale_q(start_time, AV_TIME_BASE_Q, enc->time_base);
```

there are a couple of variables that need to make clear.

the variable `filter` would be the filter buffersink, and `start_time`, in our case, would be 0, and the function
`av_buffersink_get_time_base` will return the time_base of the buffersink, which is going to be `1/60000`.

why `1/60000`?

`av_buffersink_get_time_base` actually return the time_base of the input link that points to the buffersink.

```c
format -----> buffersink
```

and if a link has no specified time_base, which means that it will not change the time_base of frames, then its time_base will
be set as the time_base of its inlink.

so, the time_base of this link would evntually be the time_base of the buffer filter, which is the time_base of your input file.

and the variable `tb` will copy the time_base of the encoder, in this case, it would be `1001/30000`, which is the reciprocal of
the average frame_rate of the input file.


and function `av_clip` is defined as follows.

```c
static av_always_inline av_const int av_clip_c(int a, int amin, int amax)
{
#if defined(HAVE_AV_CONFIG_H) && defined(ASSERT_LEVEL) && ASSERT_LEVEL >= 2
    if (amin > amax) abort();
#endif
    if      (a < amin) return amin;
    else if (a > amax) return amax;
    else               return a;
}
```

it just returns a value that is confined to the range of amin and amax, if your value is out of the boundary, then it will
just return the edge value.

and `tb.den` is 30000, and the squared root of 30000 is going to be 14.872674880270605, but the return type of `av_log2` is
going to be int, so it will just cut off the decimal part and return the integer part.

then `av_clip(29 - av_log2(tb.den), 0, 16)` can be translated into

```
extra_bits = av_clip(29 - av_log2(tb.den), 0, 16)
           = av_clip(29 - 14, 0, 16)
           = av_clip(15, 0, 16)
           = 15
```

next enlarge the `tb.den` by 2 to the power of extra_bits times.

```
tb.den <<= extra_bits
         = tb.den * (2**15)
         = 30000 * (2*15)
         = 983040000
```

notice that this would affect `enc->time_base` because tb is a value copy of `enc->time_base`.

then float_pts would be 

```
float_pts =
    av_rescale_q(frame->pts, filter_tb, tb) -
    av_rescale_q(start_time, AV_TIME_BASE_Q, tb);
```

here what `av_rescale_q` does is scale the first parameter to the base of the second parameter to the value that is on the base
of third parameter.

```

x    a
—— = ——
y    b

x is the first parameter, and y is the second parameter, and a is the b is the third parameter, and 

av_rescale_q returns a.
    
    x*b   
a = ————
     y
```

in other words, `frame->pts` is value of x, and it is on the base of its fps y, and let's calculate the pts a that is on
the base of new fps b. 

and we know that fps and time_base are the inverse of each other, and `time_base` is always a type of `AVRational`, or fraction.

that's why FFmpeg passes the time_base of the filter as the second parameter, and the enlarged time_base as the third parameter,
not just frame_rates.


```c

int64_t av_rescale_q_rnd(int64_t a, AVRational bq, AVRational cq,
                         enum AVRounding rnd)
{
    int64_t b = bq.num * (int64_t)cq.den;
    int64_t c = cq.num * (int64_t)bq.den;
    return av_rescale_rnd(a, b, c, rnd);
}
int64_t av_rescale_q(int64_t a, AVRational bq, AVRational cq)
{
    return av_rescale_q_rnd(a, bq, cq, AV_ROUND_NEAR_INF);
}
```

`av_rescale_rnd` works like

```c
int64_t av_rescale_rnd(int64_t a, int64_t b, int64_t c, enum AVRounding rnd)
{
    int64_t r = 0;
    if (rnd == AV_ROUND_NEAR_INF)
        r = c / 2;
    if (b <= INT_MAX && c <= INT_MAX) {
        if (a <= INT_MAX)
            return (a * b + r) / c;
        else {
            int64_t ad = a / c;
            int64_t a2 = (a % c * b + r) / c;
            if (ad >= INT32_MAX && b && ad > (INT64_MAX - a2) / b)
                return INT64_MIN;
            return ad * b + a2;
        }
    } 
}
```

suppose variable `a`, `b`, and `c` are less than INT_MAX, and under the `AV_ROUND_NEAR_INF` mode, `av_rescale_rnd` will just 
add a half of c to the product of a and b.

```
a * b1.num      Y * cq.num
—————————— = ——————————————————
    b1.den          cq.den

                X * bq.num * cq.den
         Y = ————————————————————————————
                    bq.den * cq.num
                    
                X * b + c/2
         Y =  ————————————————
                  c
               X * b
         Y = ———————————— + 0.5
                 c
         
         Y = Q + 0.5
```

and since `av_rescale_rnd` returns a value of type of int64_t, that really means that round the Q to the nearest integer.

why?

suppose Q is 4.41, then 4.41 plus 0.5 would be 4.91 is less than 5, then `av_rescale_rnd` will return 4.

and if Q is 4.51, then Y would 5.01, and 5 is the value returned.

and `FFSIGN` just returns 1 if the argument is greater than 0 else it will return -1. 

```c
#define FFSIGN(a) ((a) > 0 ? 1 : -1)
```

and here suppose the `frame.pts` is 1001, then float_pts would be

```
float_pts = av_rescale_q(frame->pts, filter_tb, tb) - av_rescale_q(start_time, AV_TIME_BASE_Q, tb)
          = av_rescale_q(frame->pts, filter_tb, tb) - 0
          = av_rescale_q(1001, 1/60000, 1001/983040000)
            1001 * 983040000
          = —————————————————— + 0.5
            60000 * 1001
           
          = round(16384 + 0.5)
          = 16384
          
float_pts /= 1 << extra_bits;
                16384
           =  ———————————
                1<<15
           = 0.5

float_pts += FFSIGN(float_pts) * 1.0 / (1<<17);
           = float_pts + FFSIGN(float_pts) * 1.0 / (1<<17)
           = 0.5 + FFSIGN(0.5) * 1.0 / (1<<17)
           = 0.5 + 1 * 1.0 / 1<<17
           = 0.5 + 1/1<<17
```

actually for every float_pts, FFmpeg will always add a very tiny small constant value, which is `1/1<<17` to it.

so for convenience, we use a symbol of C representing that constant, then in our case, `float_pts` would be 0.5C.
 
and `float_pts` is a very important factor for video stream simpling, we will see later.

and here `frame.pts` would be calculated as 

```c
        frame->pts =
            av_rescale_q(frame->pts, filter_tb, enc->time_base) -
            av_rescale_q(start_time, AV_TIME_BASE_Q, enc->time_base);
```

but `frame.pts` would be modified before sending to the encoder, so we just do not run the computation for `frame.pts`.

## duration

next, calculate the duration.

```c
    sync_ipts = adjust_frame_pts_to_encoder_tb(of, ost, next_picture);

    frame_rate = av_buffersink_get_frame_rate(filter);
    if (frame_rate.num > 0 && frame_rate.den > 0)
        duration = 1/(av_q2d(frame_rate) * av_q2d(enc->time_base));

    if(ist && ist->st->start_time != AV_NOPTS_VALUE && ist->st->first_dts != AV_NOPTS_VALUE && ost->frame_rate.num)
        duration = FFMIN(duration, 1/(av_q2d(ost->frame_rate) * av_q2d(enc->time_base)));
```

the `frame_rate` is the frame_rate of the graph, or the buffersink, and is equal to the frame_rate of the input file,
let's say it's denoted by `filter->frame_rate`.

and `enc->time_base` is normally is the same as the time_base of your input file if you use FFmpeg's default settings.

and in our case, `filter->frame_rate` and `enc->time_base` are reciprocal of each other, because the `frame_rate` and the
`time_base` of the encoder are both set to be the ones in the input file, meaning the output file will have the same fps as the
input file.

then the duration is going to be 1 in the first if statement.

and since `ost->frame_rate` representing the frame_rate of the out container, and is equal to the frame_rate of the encoder,
then the duration is finally calculated to be 1 in the second if statement.

this is how FFmpeg handles `frame_rate` and `time_base`, it will simply take these two settings from the input file, and pass
them to the graph, and the encoder, and the output container.

`duration` will be used along with `float_pts` and other values to compute the number of frames sent to the encoder.

## pts sequence and frame_rate

and here is another different angle to the computation of pts, which is that the pts of a frame is going to be the index times
the reciprocal of the frame_rate.

e.g. suppose for our input video file, the frame_rate is `30000/1001`, and the time_base is `1/60000`.

and the second frame, whose index is 1, has a pts of 2002, and the third frame has a pts of 4004, actually they are like

```
2002     1001
—————— = —————— * 1
60000    30000

4004     1001     4    1001
—————— = —————— * —— = —————— * 2
60000    30000    2    30000
```

and the ith frame will have a pts of `i*frame_rate`, so for a video of 30 fps, the first frame will have a pts of 1/30, and
2/30, and so on.

then you can scale the pts sequence to the base of any time_base you want. 

e.g. you want to use a time_base of 1/60000, then your pts values for the second and the third frame are going to be

```
1001*1*2       1001*2      1
—————————— = —————————— = —————— * 2001
30000         30000*2      60000

1001*2        1001*2*2      1
—————————— = —————————— = —————— * 4004
30000         30000*2      60000

```

and in practical use, for fined-grained time control, the pts for each frame is often going to be thousands, or even ten
thousands.

## nb_frames and nb0_frames

there are two variables that control the number of frames to the encoder, `nb0_frames` and `nb_frames`.

```c
nb0_frames = 0; // tracks the number of times the PREVIOUS frame should be duplicated, mostly for variable framerate (VFR)
nb_frames = 1;
```

`nb_frames` indicates the total number of frames gettting encoded, and `nb0_frames` is the number of times that the previous
frame gets encoded, and the times of the current frame getting encoded would be `nb_frames` minus `nb0_frames`.

```c
    for (i = 0; i < nb_frames; i++) {
        AVFrame *in_picture;
        int forced_keyframe = 0;
        double pts_time;

        if (i < nb0_frames && ost->last_frame) {
            in_picture = ost->last_frame;
        } else
            in_picture = next_picture;

        ost->frames_encoded++;

        ret = avcodec_send_frame(enc, in_picture);

        ost->sync_opts++;
        /*
         * For video, number of frames in == number of packets out.
         * But there may be reordering, so we can't throw away frames on encoder
         * flush, we need to limit them here, before they go into encoder.
         */
        ost->frame_number++;
    }
```

in the above loop, suppose `nb_frames` is 10, meaning that FFmpeg will encode total 10 frames here, and `nb0_frames` is 4,
meaning that we will duplicate the previous frame to the first 4 frames, and the last 6 frames are produced from the current
frame by making 6 copys of it.

```
f1 represents the previous frame, and f2 is the current frame

f1, f2 => f1,f1,f1,f1,f2,f2,f2,f2,f2,f2
```

and everytime FFmpeg sends a frame into the encoder, it will increment `ost->sync_opts` by one, then `ost->sync_opts` is the
counter of total number of frames that encoder has processed.

`nb_frames` and `nb0_frames` are heavily affected by other two variables, delta and delta0.

## delta and delta0

there are mainly 4 fps modes defined in FFmpeg, here we only concern the cfr mode, which is known as constant frame rate
which means that we want FFmpeg output a constant fps video.

and by default, if you didn't specify the fps, FFmpeg-n4.1.1 will create the output container with a fps as your input file.

and the sampling algorithm is very similar to a sliding window approach.

and `delta` and `delta0` can be viewed as the left and right boundary, and they are defined as follows:

```c
delta0 = sync_ipts - ost->sync_opts; // delta0 is the "drift" between the input frame (next_picture) and where it would fall in the output.
delta  = delta0 + duration;
```

as we can recall that `sync_ipts` is the `float_pts` returned from `adjust_frame_pts_to_encoder_tb`.

and to illustrate how this sliding window approach works, we assume that the input file has a frame_rate of `1001/30000`, now
we are processing the second frame, and it has a `time_base` of `1/60000`, and a pts of `2002`.

and what setpts does is scale the pts of the input frame by the certain factor you specified, in our case, the factor is 0.5.

and then the graph will deliver out a frame whose pts is going to be the half of its value, then `adjust_frame_pts_to_encoder_tb`
will send back a `float_pts` of 0.5C, and the `duration` would be 1, and there is one frame that has been sent to the encoder
yet, the counter `ost->sync_opts` is going to be 1.

```
    the tail of X indicates that more digits are being omited.

    delta0 = sync_ipts - ost->sync_opts;
           = 0.5C - 1
           = -0.4999X
    delta  = delta0 + duration;
           = -0.4999 + 1
           = 0.50000X
```

and let's see how the `nb_frames` and `nb0_frames` are being calculated.

```c
        case VSYNC_CFR:
            // FIXME set to 0.5 after we fix some dts/pts bugs like in avidec.c
            if (frame_drop_threshold && delta < frame_drop_threshold && ost->frame_number) {
                nb_frames = 0;
            } else if (delta < -1.1)
                nb_frames = 0;
            else if (delta > 1.1) {
                nb_frames = lrintf(delta);
                if (delta0 > 1.1)
                    nb0_frames = llrintf(delta0 - 0.6);
            }
            break;
```

basically if `frame_drop_threshold` is already specified, then drop the current frame if `delta` is less than
`frame_drop_threshold`, and by default, `frame_drop_threshold` is declared to be 0.

if `delta` is less than -1.1, then drop the current frame, if delta > 1.1, then duplicate frames, and besides, if `delta0`
is greater than 1.1 too, then FFmpeg will encode the previous frame.

so put differently, if `delta` is in the range from -1.1 to 1.1, both sides inclusive, then encode only the current frame once.

and by the way, `lrintf` just rounds the value you put in to integer, for instance, `lrintf(1.1)` and `lrintf(1.4)` are going
to be 1, and `lrintf(1.5)` is going to be 2.

## Sliding window sampling

but what `delta0` and `delta` really mean in this sampling?

let's take a look at the comments made for `delta0`.

> delta0 is the "drift" between the input frame (*next_picture*) and where it would fall in the output.

the term drift is really the key, from our understandings, delta0 indicates the point into which current frame falls, and
`os->sync_opts` is the point that it should be.

in the example, `sync_ipts` is 0.5C, and `os->sync_opts` is 1, which means that this frame should be placed at index 1, but now
it lands at index 0.5C, let's call `sync_ipts` the P point of the current frame.

but should we just drop it or duplicate it? this depends on how far it falls behind, and this is where `delta` and `duration`
come to play.

first, let's translate the equation calculating delta.

let's say that `ost->sync_opts` is the right boundary, let's call it R, and L is the left boundary, they are apart at a
distance of `duration`. 

```
delta0 = sync_ipts - ost->sync_opts

       = P - R

delta = delta0 + duration

      = sync_ipts - ost->sync_opts + duration

      = sync_ipts - (ost->sync_opts - duration)
      
      = sync_ipts - (R - duration)

      = sync_ipts - L
      
      = P - L
```

and  `delta0` is going to be the distance from R to the P, and `delta` is going to be the distance from P to L.

if `delta` is less than 0, then we might want to drop this frame.

```
           <-----------------delta0----------------->

sync_ipts(P)                    L                       ost->sync_opts(R)
            <-----delta------>    <----duration------->               

```

if P is far more behind L, `delta` is less than -1.1, then drop the current frame.

if `delta` is greater 0, but `detal0` is still less than 0, then we have 

```

       <---delta--->              <---delta0----->

     L               sync_ipts(P)                  ost->sync_opts(R)

       <-------------------duration--------------->               


```

if `delta` is larger than the threshold value, which is 1.1, then duplicate the frame.

if `delta0 > 0` and `delta > 0`, then we have

```

                                   
     <--duration--->                  <---delta0--->
   L                 ost->sync_opts(R)               sync_ipts(P)
               

    <---------------------------delta---------------->

```

and if `delta0` is greater than 1.1, then in addition to duplicating the current frame, we need to duplicate the previous frame
as well, in this case, P is far more ahead of R.


below will show you how `delta` and `delta0` change when the frames come out of the graph.

```

duration=1

pts       pts from setpts      sync_ipts(P)    ost->sync_opts(R)     delta0       delta         nb_frames

0               0               -1/(1<<17)     0                     -1/(1<<17)    0.99999           1 


2002           1001             0.5xxxx        1                     -0.499xxx     0.5000xxxx        1


4004           2002             1.00xxx        2                      -0.99999x     1<<17            1


6006           3003             1.500xx        3                      -1.4999xx     0.49999x         1


8008           4004             2.0000x        4                      -1.99999x     -0.99999         1

10010          5005             2.5000x        5                      -2.49999x     -1.49999         0

12012          6006             3.0000x        5                      -1.99999x     -0.99999         1

14014          7007             3.5000x        6                      -2.49999x     -1.49999         0


```

and notice that if we are dropping the current frame, then R would remain unchanged, which means that the frame at index R
would be determined by the next frame.

and this is what is going on when we set filter_complex as `setps=2*PTS`.

```

duration=1

pts       pts from setpts       sync_ipts(P)    ost->sync_opts(R)     delta0        delta          nb_frames

0               0               -1/(1<<17)       0                    -1/(1<<17)      0.99999           1 


2002           4004             2.000xx          1                    1.00000x        2.00000x          2


4004           8008             4.00xxx          3                    1.00000x        2.00000x          2


6006           12012            6.00xx           5                    1.00000x        2.00000x          2


8008           16016            8.0000x          7                    -1.00000x       2.00000x          2

```

# the hanges in FFmpeg-n6-1-1 

the idea for audo and video sampling follows the one in n4.4.1, but there are some changes in implementation details.

## duration

the variable `nb0_frame` is renamed to `nb_frames_prev`, which makes it what-you-see-is-what-you-get.

and the calculation of `nb0_frame` and `nb_frames_prev` is moved to a function named `video_sync_process`.

in `video_sync_process`, it simplies the computation of `duration`, and only needs `frame->time_base` and `ofp->tb_out`, and
the variable `ftp` is the reference of the ouput filter.

```c
duration = frame->duration * av_q2d(frame->time_base) / av_q2d(ofp->tb_out);
```

in general, `ofp->tb_out` will be the inverse of the `frame_rate` of the output stream, and if nothing special happend, that
the `frame_rate` of the output stream should be the same as the input stream.

the invoking chain is going to be

```
fg_output_step -> fg_output_frame -> video_sync_process
```

in `fg_output_step`, first FFmpeg will set `frame->time_base` as the time base of the buffersink filter.

```c
static int fg_output_step(OutputFilterPriv *ofp, int flush)
{
    FilterGraphPriv    *fgp = fgp_from_fg(ofp->ofilter.graph);
    OutputStream       *ost = ofp->ofilter.ost;
    AVFrame          *frame = fgp->frame;
    
    ret = av_buffersink_get_frame_flags(filter, frame,
                                        AV_BUFFERSINK_FLAG_NO_REQUEST);
                                        
    frame->time_base = av_buffersink_get_time_base(filter);
    
    // Choose the output timebase the first time we get a frame.
    if (!ofp->tb_out_locked) {
        ret = choose_out_timebase(ofp, frame);
        if (ret < 0) {
            av_log(ost, AV_LOG_ERROR, "Could not choose an output time base\n");
            av_frame_unref(frame);
            return ret;
        }
    }
    
    ret = fg_output_frame(ofp, frame);
}
```

and then choose the proper time_base for the frame in the function `choose_out_timebase`.

and in most case, `choose_out_time_base` works as follows

```c
static av_always_inline AVRational av_inv_q(AVRational q)
{
    AVRational r = { q.den, q.num };
    return r;
}

static int choose_out_timebase(OutputFilterPriv *ofp, AVFrame *frame)
{
    AVRational        tb = (AVRational){ 0, 0 };
    
    FPSConvContext   *fps = &ofp->fps;
    
    fr = fps->framerate;
    
    if (!(tb.num > 0 && tb.den > 0))
        tb = av_inv_q(fr);
    if (!(tb.num > 0 && tb.den > 0))
        tb = frame->time_base;

finish:
    ofp->tb_out        = tb;
    fps->framerate     = fr;
    ofp->tb_out_locked = 1;

    return 0;
}
```

and `fr` is the fps of your output stream, and then the variable `tb` will have `fr.den` as the numerator, and `fr.num` as the
denumerator(see `av_inv_q`).

## float_pts

the variable `float_pts` will be calculated as 

```c
    AVRational        tb = tb_dst;
    AVRational filter_tb = frame->time_base;
    float_pts = av_rescale_q(frame->pts, filter_tb, tb) -
                av_rescale_q(start_time, AV_TIME_BASE_Q, tb);

```

and compared to FFmpeg-n4.4.1

```c
        AVRational filter_tb = av_buffersink_get_time_base(filter);
        frame->pts =
            av_rescale_q(frame->pts, filter_tb, enc->time_base) -
            av_rescale_q(start_time, AV_TIME_BASE_Q, enc->time_base);

```

the `enc->time_base` is replaced with `tb_dst`, which is also pointing to `ofp->tb_out`.

```c
sync_ipts = adjust_frame_pts_to_encoder_tb(frame, ofp->tb_out, ofp->ts_offset);
```

but we rather take this as a more clear name than a change, because often the frame_rate for the encoder and the one for the
output stream are often equal, and normally the `time_base` for the encoder is the inverse of its frame_rate.

and `filter_tb` being modified to `frame->time_base` is another name changing.

and whether adding the constant value `1.0/(1<<17)` or not now is based on the round of the `float_pts` in comparsion with n4.4.1.

but this does not affect the results of the sliding window approach.

```

duration=1

pts       pts from setpts      sync_ipts(P)    ost->sync_opts(R)     delta0       delta         nb_frames

0               0               0              0                      0            1                 1 


2002           1001             0.5xxxx        1                     -0.499xxx     0.5000xxxx        1


4004           2002             1              2                      -1           0                 1


6006           3003             1.500xx        3                      -1.4999xx     0.49999x         1

8008           4004             2              4                      -2            -1               1

10010          5005             2.5000x        5                      -2.49999x     -1.499999        0

```
