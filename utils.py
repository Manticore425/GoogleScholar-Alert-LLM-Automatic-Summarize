class Paper_query:
    def __init__(
        self,
        query,
        key_word="",
        page_num=2,
        max_results=3,
        days=10,
        sort="web",
        save_image=False,
        file_format="md",
        language="en",
    ):
        self.query = query
        self.key_word = key_word
        self.page_num = page_num
        self.max_results = max_results
        self.days = days
        self.sort = sort
        self.save_image = save_image
        self.file_format = file_format
        self.language = language

    def get_query(self):
        return self.query

    def get_pag_num(self):
        return self.pag_num

    def get_max_results(self):
        return self.max_results

    def get_days(self):
        return self.days

    def get_sort(self):
        return self.sort

    def get_save_image(self):
        return self.save_image

    def get_file_format(self):
        return self.file_format

    def get_language(self):
        return self.language

    def get_key_word(self):
        return self.key_word
