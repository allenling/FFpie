


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

and without the help of that programmatcial interfaces, you will not be able to control your encoding flow in such a
fine-grained fashion.

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

## Tokenization

and actually you can further shorten the serialized string of the graph. 

a simple and interesting apporach is split the serialized string into multiple portions of equal size, and calculate a hash or
id for every portion, and concatenate all the ids.

one approach we employed is to use redis to store those portions in sperately sorted sets.

for instance, suppose that the serialized string is divided into 5 smaller chunks, each chunk has a size of 100.

and then there will be 5 sorted sets to store those subchunks, and the first chunk, the first 100 characters will be saved in
first sorted set named s1, and the second subchunk will be stored in the second sorted set named s2, and so on.

the idea is that the token for a chunk in the sorted set will be its index in the sorted set.

but sortedsets are not lists, items are unordered in a sorted set, meaning you can not access the items left to right one by one.

you can not access the first, the third, or the fifth item in a sorted set.

how can you determine the index for an item? 

as sortedsets hold scores for all the items, so you can assign the item a score, which can be viewed as the index for the item.

suppose sorted set `s1` has 5 items right now, and for a newly inserted item, its index or score will be 6.

but there's a couple of problems.

first, there's a chance that two clients assign same score or index for two different keys.

actually it's highly likely in a concurrent system, for instance, client A asked redis for the size of the sorted set `s1`,
and redis returned it 5, and client B asked redis for the size of `s1`, it would get 5.

then client A would add key `k1` into `s1` with a score of 6, and client B would add key `k2` into `s1` as well with the
same score of 6, a conflict happens.

so to solve this problem, we introduce another key, a key represents the size of the sorted set, let's call this key the amount key.

so to get the score of an item, we would not rely on redis for the size, we just increase the amount key by 1.

since redis processes commands concurrently meaning each comand will be processed atomically, so client A and client B will
have different scores for their keys.

and there's another dirty data scenario where two clients trying to add the same key into the sorted set.

and since clients would always get different scores from that amount key, them the score for the key would be covered later.

to prevent this from happening, you can set the `NX` option to be true when you call the command `sadd`, then redis would insert
new item only, and if that item is already existed in the sorted set, then redis would decide not to perform the `sadd` action.


# CFR sampling

a detailed and structural explanation on FFmpeg's CFR algorithm is presented in `docs/how_FFmpeg_speeds_up_a_video.md`. 

# concat and demuxing 

just a series of simple calculations on dts and pts sequence, for more information, please check out `docs/FFmpeg_concat_demuxer.md`.


