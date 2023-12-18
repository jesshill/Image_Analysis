class ImageID:
    def __init__(self):
        self._PATH = "/Users/amoore/projects/stable_txts/img_id.txt"
        with open(self._PATH, "r") as f:
            for line in f:
                self._CURR = line
            f.close()
        self._CURR_INT = int(self._CURR)


    def get_nums(self, n):
        ids = []
        for i in range(n):
            ids.append(f"{(self._CURR_INT + i)}".zfill(5))

        self._CURR_INT += n
        self._CURR = str(self._CURR_INT).zfill(5)

        self._update_file()

        return ids

    def _update_file(self):
        with open(self._PATH, "w") as f:
            f.write(self._CURR)
            f.close()
