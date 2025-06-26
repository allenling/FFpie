


import redis


class TokenCls:

    def get_token(self, graph_bytes) -> str:
        raise NotImplementedError

    def from_token(self, token) -> bytes:
        raise NotImplementedError


class RedisToken(TokenCls):

    slice_size = 100
    chunk_zset_key = "graph_chunks_level:{idx}"
    chunk_amount_key = "graph_chunk_amcount:{idx}"

    def __init__(self, con=None):
        self.con = con or redis.Redis()
        return

    def get_token(self, graph_bytes) -> str:
        slices = [graph_bytes[i * self.slice_size:(i + 1) * self.slice_size] for i in
                  range(len(graph_bytes) // self.slice_size + 1)]
        params = []
        for idx, chunk in enumerate(slices):
            chunk_zset = self.chunk_zset_key.format(idx=idx)
            params.append([chunk_zset, chunk])
        pipeline = self.con.pipeline()
        for chunk_zset, chunk in params:
            pipeline.zscore(chunk_zset, chunk)
        ret = pipeline.execute()
        missing_keys = []
        token = []
        for idx, num in enumerate(ret):
            if num is None:
                missing_keys.append([idx, slices[idx]])
                sc = None
            else:
                sc = str(int(num))
            token.append(sc)
        if not missing_keys:
            return "_".join(token)
        for idx, chunk in missing_keys:
            chunk_amount_key = self.chunk_amount_key.format(idx=idx)
            pipeline.incrby(chunk_amount_key)
        ret = pipeline.execute()
        for num, chunk_info in zip(ret, missing_keys):
            idx, chunk = chunk_info
            chunk_zset = self.chunk_zset_key.format(idx=idx)
            pipeline.zadd(chunk_zset, mapping={chunk: num}, nx=True)
        pipeline.execute()
        for idx, chunk in missing_keys:
            chunk_zset = self.chunk_zset_key.format(idx=idx)
            pipeline.zscore(chunk_zset, chunk)
        ret = pipeline.execute()
        for num, info in zip(ret, missing_keys):
            chunk_idx = info[0]
            token[chunk_idx] = str(int(num))
        return "_".join(token)

    def from_token(self, token) -> bytes:
        chunks = token.split("_")
        p = self.con.pipeline()
        for index, num in enumerate(chunks):
            key = self.chunk_zset_key.format(idx=index)
            num = int(num)
            p.zrangebyscore(key, min=num, max=num)
        ret = p.execute()
        data = b"".join([i[0] for i in ret])
        return data



def main():
    return


if __name__ == "__main__":
    main()
