class ReaderAgent:
    def __init__(self):
        pass

    def read_file(self, file_path: str) -> str:
        with open(file_path, 'r') as file:
            return file.read()

