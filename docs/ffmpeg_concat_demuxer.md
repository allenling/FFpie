

# concat demuxer

FFmpeg-n4.1.1.

the idea is quite simple, which is that FFmpeg will use the duration of the previous video file as the start time of the
current video file. 

the command

```
ffmpeg -f concat -safe 0 -i concat_files.txt -c copy -y output.mp4
```

and the content of th econcat_files.txt looks like

```
file 'f1.mp4'
file 'f2.mp4'
```

to use concat demuxer, FFmpeg requires that

> All files must have the same streams (same codecs, same time base, etc.) but can be wrapped in different container formats.

# duration

the duration of a stream is the value calculated as the pts of the last packet logical plus the duration of that packet.

notice that the packet must be the one that is displayed last logically, because if you encoded a file with B frames, then the last
packet in sequence might not be the one gets displayed the last.

suppose that the first input file has a time_base of `1/30000`, and the last packet will be displayed at the time `7530523`
representing at 251.017433 seconds, and it has a duration of 1001, then the next packet should be placed at pts 
`7530523 + 1001 = 7531524`.

remember that one of the requirement for concat demuxer is going to be `all files must have the same time_base`. 

and if a media file has more than one streams, and the duration of the file is going to be the largest duration among all the
streams.

so the first packet of the next file is going to be the start time plus the last duration.

that's it, that's how FFmpeg's concat demuxer works.

```c

static int open_file(AVFormatContext *avf, unsigned fileno)
{
    // concatdec.c:353
    cat->cur_file = file;
    file->start_time = !fileno ? 0 :
                       cat->files[fileno - 1].start_time +
                       cat->files[fileno - 1].duration;
    file->file_start_time = (cat->avf->start_time == AV_NOPTS_VALUE) ? 0 : cat->avf->start_time;
    file->file_inpoint = (file->inpoint == AV_NOPTS_VALUE) ? file->file_start_time : file->inpoint;
    file->duration = get_best_effort_duration(file, cat->avf);
}
```

`file->start_time` will be 0 if the current file is the first file in the `files` array, else the `start_time` will be set to
be the logical last time of the last file.

suppose the previous file starts at time 10, and last 10.5 seconds, then the current file would start at second 20.5.

FFmpeg will translate the float time to an integer on the base of 1,000,000, so if the start time for current file is going to
be 20,500,000.

and next, modify the pts and dts of every packet from the current file.

```c


static int concat_read_packet(AVFormatContext *avf, AVPacket *pkt)
{
    // concatdec.c:618
    delta = av_rescale_q(cat->cur_file->start_time - cat->cur_file->file_inpoint,
                         AV_TIME_BASE_Q,
                         cat->avf->streams[pkt->stream_index]->time_base);
    if (pkt->pts != AV_NOPTS_VALUE)
        pkt->pts += delta;
    if (pkt->dts != AV_NOPTS_VALUE)
        pkt->dts += delta;
}
```

basically every packet will have its pts and dts increased by `delta`, which can be considered as the `start_time` the
current_file, as generally, `cat->cur_file->file_inpoint` would be 0.



