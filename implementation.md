


# FFmpeg flow

what's happening inside when you run FFmpeg command line to edit your video file? 

FFmpeg's worker flow can be divided into 4 steps in order.

1. decode and read frames from the input container.
2. apply the graph to the frames.
3. sample and async the frames, encode the frames.
4. write into the output container.

we bring this pipeline into a class called Clips.

when you create and run a clip instance, it will do all those things for you automatically to mimic the pipeline in FFmpeg.

the visualization of how a clip works inside can be described as follows:

```

                           input1 input2 ...           input1 input2 ...
                            |      |                      |     |
                            v      v                      v     v
                           +--------------------+      +--------------------+
                           |Video Graph(filters)|      |Audio Graph(filters)| 
                           +--------------------+      +--------------------+
                           |                           |
                           v                           v
                           S(sampling)                 S(sampling)
                           |                           |
                           v                           v
                           E(encoding)                 E(encoding)
                           |                           |
                           v                           v
output container:         video stream                 audio stream
                         

```


# graph serialization

a graph is made up of head-to-tail linking filters, and a graph can be seen as a tree.

an example looks like

```

                 branc1          branc2                              brach4
        mp4  -->  split --> scale --> hflip ------>  hstack ---> overlay --> hflip --> output
                    |                                ^             ^
                    |                                |             |
                    +-----> scale --> vflip ---------+            png
                           branch3


```

to serialize the tree to make sure we can produce a unique string representing that graph, we have to traverse through the tree.

and because the inputs and the outputs of a filter are indexed from 0, we can traverse its inputs and outputs in an order from left to rigth
to have a unique path for the filter.

and then DFS is a feasiable algorithm to use to traverse the tree in order to get that unqiue serialization result. 

and actually you can further shorten the serialized string of the graph. 

a simple and fun apporach is split the serialized string into multiple portions of equal size, and calculate a hash or id for every
portion, and concatenate all the ids.

one approach we employed is use redis to store those portions in serveral sorted sets.

and every portion or chunk will be assigned a socre that is the position of that chunk in the sorted set.

e.g. suppose we have five chunks, `c1`, `c2`, `c3`, `c4`, `c5`, and they are going to be put into five sorted sets, `s1`, `s2`, `s3`,
`s4`, `s5` respectively.

```
serialized string: c1c2c3c4c5
sorted sets      : s1s2s3s4s5   
```

and to calculate the id for chunk `c1`, first get the assoicated score of `c1` in `s1`.

if `c1` is in `s1` already, then its score will be the id for `c1`.

if `c1` is not in `s1`, then get the total number of items in `s1`.

suppose there are five items in `s1` now, and that number will be the score for `c1` in `s1`, and then push `c1` into `s1` with a score of 5.

connecting those ids one after one you will have a unique token for that serialized string.

to deserailize a given string, just repeat the procedure but in reverse.

for each id in the token, send a command `zrangebyscore` to redis to get the key by the score or the id, and the key will be the chunk.  

and joining all the chunks you will get the complete original serialized string.

as you can imagine, this might cause a concurrent problem of inconsistent data when there are two different serialized strings bearing
the same portion at the same position.

suppose we have two serialized strings, `str1` and `str2`, and they are both starting with a chunk of `cx`.

and suppose `cx` is not in the sorted set `s1`, and `s1` contains 6 items right now.

so `str1` and `str2` both know the fact that `cx` is a new item for `s1` and start to put `cx` in `s1. 

and first, `str1` will ask `s1` the number of items in `s1`, it will have 6 in return, and `str1` will assign a score of 6 to the
chunk `cx`, and now `s1` contains 7 items in total.

and then `str2` make a query to `s1` how many items it has in it, and `str2` will get 7 in return, and `st2` will assoicate `cx` with
a score of 7.

then the id that `str1` got for the chunk `cx` has changed.

luckily, redis can help us with this inconsistency.

all we have to do is set the paramter `nx` as `True` for function `zadd` that you use to add a chunk to the sorted set.

`nx` will prevent `str2` from setting a score of 7 for `cx` because `cx` is already in there.

and `str1` and `str2` will have to request redis one more time to get the latest score assigned to `cx`.  

# CFR sampling

a detailed and structural explanation on FFmpeg's CFR algorithm is presented in `docs/how_FFmpeg_speeds_up_a_video.md`. 

# concat and demuxing 

just a series of simple calculations on dts and pts sequence, for more information, please check out `docs/FFmpeg_concat_demuxer.md`.


