class Post:
    def __init__(self):
        self.id = ""
        self.type = "facebook page"
        self.time_crawl = ""
        self.link = ""
        self.author = ""
        self.author_link = ""
        # self.key_word = ""
        # self.field = ""
        self.content = ""
        self.created_time = ""
        # self.Interactive = 0
        # self.spread = 0
        self.comment = 0
        self.like = 0
        self.haha = 0
        self.wow = 0
        self.sad = 0
        self.love = 0
        self.care = 0
        self.angry = 0
        self.share = 0
        self.avatar = ""
        # self.evaluate = "positive"
        # self.location = "unknown"
        # self.gender = "unknown"
        # self.job = "unknown"
        # self.relationship = "unknown"
        # self.age2 = 0
        # self.area = "unknown"
        # self.academic = "unknown"
        # self.source_classify = "unknown"
        # self.post_classify = "unknown"
        self.image_url = []
        self.video = []
        # self.image_key = "unknown"
        # self.evaluate_level_2 = 0
        # self.real_crises_score = 0
        # self.crises_score = 0
        # self.content_length = 0
        # self.real_evaluate = "unknown"
        # self.similar_count = 0
        # self.similar_group_id = "unknown"
        # self.similar_master = 1
        # self.title = "unknown"
        self.domain = "https://www.facebook.com"
        self.source_id = ""
        # self.content_post = ""
        # self.id_page_group = ""
        # self.href_reply = ""
        # self.dataInListComments = []
        #self.post_share = None
        self.hashtag = []
        # self.description = ""
        # self.music = ""
        # self.title = ""
        # self.duration = 0
        # self.view = 0

    def is_valid(self) -> bool:
        is_valid = self.id != "" and self.author != "" and self.link != "" and self.created_time 
        return is_valid

    def __str__(self) -> str:
        string = ""
        for attr_name, attr_value in self.__dict__.items():
            string =  f"{attr_name}={attr_value}\n" + string
        return string