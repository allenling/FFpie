


import cv2 as cv

import ffpie

from ffpie.graph.token import RedisToken



def graph_serialization():
    """
    you can store that consistent serialized bytes of your graph anywhere you want.

    the positions of your inputs will rely on sort of upside-down preorder traversal, you do not have to rely on the names.

    to run the graph, deserialize/de-tokenize the bytes, and pass in preorder inputs.
    """
    v1_path = r"D:\Downloads\yellowstone.mp4"
    v2_path = r"D:\Downloads\yosemiteA.mp4"
    v3_path = r"D:\Downloads\73602_85f0a86824d34462bb728c.png"
    s1 = ffpie.Source(v1_path)
    s2 = ffpie.Source(v2_path)
    lay_s = ffpie.ImageReader(v3_path)
    v1 = ffpie.Buffer(template=s1.video_stream, name="v1")
    v2 = ffpie.Buffer(template=s2.video_stream, name="v2")
    v3 = ffpie.Buffer(template=lay_s.stream, name="v3")
    #
    g = ffpie.Graph(v1, v3)
    b1_start, b1_end = g.link_filters(ffpie.Split(name="s1"))
    b2_start, b2_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.HFlip())
    b3_start, b3_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.VFlip())
    b4_start, b4_end = g.link_filters(ffpie.HStack(), ffpie.Overlay(name="o1"), ffpie.HFlip())
    g.link(b1_end, b2_start, 0, 0)
    g.link(b1_end, b3_start, 1, 0)
    g.link(b2_end, b4_start, 0, 0)
    g.link(b3_end, b4_start, 0, 1)
    #
    bytes1, leaves1 = g.serialize()
    print(bytes1)
    print(leaves1)
    g.mark_input_output()
    bytes2, leaves2 = g.serialize()
    print(bytes2)
    print(leaves2)
    print(bytes1 == bytes2)
    inputs = [v1, v2, v3]
    inputs_map = {}
    for i in inputs:
        inputs_map[i.name] = i
    preorder_inputs = []
    for fname, _ in leaves2:
        preorder_inputs.append(inputs_map[fname])
    print(preorder_inputs)
    new_g = ffpie.Graph.deserialize(bytes2)
    bytes3, leaves3 = new_g.serialize()
    print(bytes3)
    print(leaves3)
    print(bytes1 == bytes3)
    new_g.set_inputs(*preorder_inputs)
    bytes4, leaves4 = new_g.serialize()
    print(bytes4)
    print(leaves4)
    print(bytes1 == bytes4)
    #
    redis_token = RedisToken()
    redis_token.con.delete(redis_token.chunk_zset_key)
    redis_token.con.delete(redis_token.chunk_amount_key)
    bytes5, leaves5 = new_g.serialize()
    token1 = redis_token.get_token(bytes5)
    print(token1)
    print(leaves5)
    print(bytes1 == bytes5)
    #
    bytes6 = redis_token.from_token(token1)
    tg = ffpie.Graph.deserialize(bytes6)
    bytes7, leaves7 = tg.serialize()
    print(bytes7)
    print(leaves7)
    print(bytes1 == bytes7)
    tg.set_inputs(*preorder_inputs)
    #
    for f1, f2 in zip(s1.read_video_frames(), lay_s.read_video_frames()):
        outframe = tg.apply_frames(f1, f2)[0]
        cv_frame = outframe.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    s1.close()
    lay_s.close()
    return



def main():
    graph_serialization()
    return


if __name__ == "__main__":
    main()
