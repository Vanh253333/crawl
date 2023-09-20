import time
from typing import Callable, List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from post_extractor import PostExtractor
from post_desktop_extractor import PostDesktopExtractor
from post_mobile_extractor import PostMobileExtractor
from selenium_utils import SeleniumUtils
from utils.log_utils import logger
from utils.common_utils import CommonUtils
from post_model import Post
import json
from unidecode import unidecode
from selenium.webdriver.common.action_chains import ActionChains
from utils.utils import write_data_to_file, read_data_from_file
import queue
import threading
import re

class PostElementIterator:
    def __init__(self, post_element_list: List[WebElement]):
        self.post_element_list = post_element_list
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.post_element_list):
            raise StopIteration

        post = self.post_element_list[self.index]
        self.index += 1
        return post
    
    def _len(self):
        return len(self.post_element_list)

    def update(self, post_element_list: List[WebElement]):
        self.post_element_list = post_element_list

class PostMobileSearchExtractor:
    driver: WebDriver
    FACEBOOK_SEARCH_LINK: str = "https://m.facebook.com/search/posts?q="
    RECENT_POST_FILTER: str = "&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"
    POST_CONTENT_XPATH: str = './/div[@data-gt=\'{"tn":"*s"}\']'
    POST_SHARE_CONTENT_XPATH: str = './/div[@data-gt=\'{"tn":"*s"}\']'

    BACK_NAVIGATION_BAR_XPATH: str = '//a[@data-sigil="MBackNavBarClick"]'
    POST_XPATH: str = "//div[contains(@class, 'async_like')]"
    POST_SHARE_XPATH: str = '//div[contains(@class, "async_like")]//div[contains(@class, "async_like")]'
    posts: List[Post] = []
    callback: Optional[Callable[[Post], None]] = None

    def __init__(self, driver: WebDriver, keyword: str, keyword_noparse: List, callback: Optional[Callable[[Post], None]] = None):
        self.url = f"{self.FACEBOOK_SEARCH_LINK}{keyword}{self.RECENT_POST_FILTER}"
        self.callback = callback
        self.driver = driver
        self.driver.get(self.url)
        self.driver.implicitly_wait(1000)
        self.keyword_noparse = keyword_noparse
        slept_time = CommonUtils.sleep_random_in_range(1, 5)
        logger.debug(f"Slept {slept_time}")

    def _get_current_post_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(By.XPATH, self.POST_XPATH)
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def _get_post_share_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(By.XPATH, self.POST_SHARE_XPATH)
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_SHARE_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def _get_current_post_element_list(self) -> Tuple[List[WebElement], int]:
        post_element_list: List[WebElement] = []
        try:
            self.driver.implicitly_wait(5)
            post_element_list = self.driver.find_elements(By.XPATH, self.POST_XPATH)
            post_element_list_size = len(post_element_list)
            logger.debug(f"So bai post hien thi tren giao dien: {post_element_list_size}")
            return post_element_list, post_element_list_size
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_XPATH}")
            return post_element_list, 0
        except Exception as e:
            logger.error(e, exc_info=True)
            return post_element_list, 0

    def unsigned_text(self, content : str):
        return unidecode(content).lower()

    def get_key_subkey(self, keyword_list_raw: str) -> List[str]:
        keyword_list_raw_dict = json.loads(keyword_list_raw)
        keyword_list = []
        subkey_list  = []
        # Lặp qua mỗi dict trong danh sách
        for item in keyword_list_raw_dict:
            item_key = {}
            # Lấy giá trị của key
            key = item['key']
            item_key['key'] = self.unsigned_text(key)
            # Lặp qua mỗi giá trị trong subKey
            for subkey in item['subKey']:
                subkey_list.append(self.unsigned_text(subkey))
                # Thêm từ khóa kết hợp vào danh sách keywords
            item_key['subkey'] = subkey_list
            keyword_list.append(item_key)

        return keyword_list

    def start(self) -> List[Post]:
        post_element_list, post_element_list_size = self._get_current_post_element_list()
        post_element_iterator = PostElementIterator(post_element_list=post_element_list)
        key_unsigned = self.get_key_subkey(self.keyword_noparse)
        while post_element_iterator.index < 20:
            try:
                post_element = next(post_element_iterator)
                self._enter_post(post_element)

                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                logger.debug(f"Slept {slept_time}")
                post_element = self._get_current_post_element()
                if post_element:
                    post_share_element = self._get_post_share_element()
                    isPostShare = True if post_share_element else False
                    post_extractor: PostMobileExtractor = PostMobileExtractor(driver=self.driver, post_element=post_element)
                    post = post_extractor.extract()
                    retry_time = 0
                    def retry_extract(post, retry_time):
                        while not post.is_valid():
                            post = post_extractor.extract()
                            if retry_time > 0:
                                logger.debug(f"Try to extract post {retry_time} times {str(post)}")
                                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                                logger.debug(f"Slept {slept_time}")
                            retry_time = retry_time + 1
                            if retry_time > 20:
                                logger.debug("Retried 20 times, skip post")
                                break
                        return
                    retry_extract(post, retry_time)
                    #---Quan--12/7/2023 2:48:00-- lọc những bài viết không liên quan đến từ khóa
                    def filter_post(post):
                        logger.debug("-----______----------")
                        contents_unsigned = self.unsigned_text(post.content)
                        for item_key in key_unsigned:
                            if item_key['key'] in contents_unsigned:
                                for sub_k in item_key['subkey']:
                                    if sub_k in contents_unsigned:
                                        self.posts.append(post)
                                        break
                    filter_post(post)
                    if isPostShare:
                        enter_post_share = self._enter_post_share(post_share_element)
                        slept_time = CommonUtils.sleep_random_in_range(1, 3)
                        logger.debug(f"Slept {slept_time}")
                        post_share_element = self._get_current_post_element()
                        slept_time = CommonUtils.sleep_random_in_range(1, 5)
                        logger.debug(f"Slept {slept_time}")
                        if post_share_element:
                            post_share_extractor: PostMobileExtractor = PostMobileExtractor(driver=self.driver, post_element=post_share_element)
                            post_share = post_share_extractor.extract()
                            retry_time = 0
                            retry_extract(post_share, retry_time)
                            #post.post_share = post_share
                            filter_post(post_share)
                            if enter_post_share is not None:
                                self._back()
                                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                                logger.debug(f"Slept {slept_time}")

                    # while not post.is_valid():
                    #     post = post_extractor.extract()
                    #     if retry_time > 0:
                    #         logger.debug(f"Try to extract post {retry_time} times {str(post)}")
                    #         slept_time = CommonUtils.sleep_random_in_range(1, 5)
                    #         logger.debug(f"Slept {slept_time}")
                    #     retry_time = retry_time + 1
                    #     if retry_time > 20:
                    #         logger.debug("Retried 20 times, skip post")
                    #         break
                    
                    if self.callback:
                        self.callback(post)

                self._back()
                #self._back()
                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                logger.debug(f"Slept {slept_time}")

                post_element_list, post_element_list_size = self._get_current_post_element_list()
                post_element_iterator.update(post_element_list=post_element_list)
            except StopIteration as e:
                logger.debug(f"Đã hết post của từ khóa")
                break
        return self.posts

    def _get_post_content_element(self, post_element: WebElement) -> WebElement:
        return post_element.find_element(by=By.XPATH, value=self.POST_CONTENT_XPATH)
            
    def _enter_post(self, post_element: WebElement):
        logger.info("Start")
        post_content_element = self._get_post_content_element(post_element=post_element)
        a_post_content_element = post_content_element.find_element(by=By.XPATH, value='.//a[@aria-label]')
        SeleniumUtils.click_element(driver=self.driver, element=a_post_content_element)
        logger.info(f"End")

    def _get_post_share_content_element(self, post_element: WebElement) -> WebElement:
        return post_element.find_element(by=By.XPATH, value=self.POST_SHARE_CONTENT_XPATH)

    def _enter_post_share(self, post_element: WebElement):
        logger.info("Start")
        try:
            # post_content_element = self._get_post_share_content_element(post_element=post_element)
            a_post_content_element = post_element.find_element(by=By.XPATH, value='.//div[@data-sigil="m-feed-voice-subtitle"]//a')
            SeleniumUtils.click_element(driver=self.driver, element=a_post_content_element)
            
        except NoSuchElementException:
            logger.error(f"Not found xpath enter post share")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        logger.info(f"End")
        return 1

    def _get_back_navigation_bar_element(self) -> WebElement:
        return self.driver.find_element(by=By.XPATH, value=self.BACK_NAVIGATION_BAR_XPATH)
        
    def _back(self):
        logger.info("Start")
        back_navigation_bar_element = self._get_back_navigation_bar_element()
        SeleniumUtils.click_element(driver=self.driver, element=back_navigation_bar_element)
        logger.info("End")


class PostDesktopSearchExtractor:
    driver: WebDriver
    FACEBOOK_SEARCH_LINK: str = "https://www.facebook.com/search/posts?q="
    RECENT_POST_FILTER: str = "&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"
    POST_XPATH: str = './/div[@aria-posinset]'
    POST_FIRST_XPATH: str = './/div[@aria-posinset="1"]'
    POST_SHARE_XPATH: str = ".//div[@class='x1y332i5']" 
    posts: List[Post] = []
    callback: Optional[Callable[[Post], None]] = None

    def __init__(self, driver: WebDriver, keyword: str, keyword_noparse: List, callback: Optional[Callable[[Post], None]] = None):
        self.url = f"{self.FACEBOOK_SEARCH_LINK}{keyword}{self.RECENT_POST_FILTER}"
        self.callback = callback
        self.driver = driver
        self.driver.get(self.url)
        self.driver.implicitly_wait(1000)
        self.keyword_noparse = keyword_noparse
        slept_time = CommonUtils.sleep_random_in_range(1, 5)
        logger.debug(f"Slept {slept_time}")

    def _get_current_post_element_list(self) -> Tuple[List[WebElement], int]:
        post_element_list: List[WebElement] = []
        try:
            self.driver.implicitly_wait(5)
            post_element_list = self.driver.find_elements(By.XPATH, self.POST_XPATH)
            post_element_list_size = len(post_element_list)
            logger.debug(f"So bai post hien thi tren giao dien: {post_element_list_size}")
            return post_element_list, post_element_list_size
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_XPATH}")
            return post_element_list, 0
        except Exception as e:
            logger.error(e, exc_info=True)
            return post_element_list, 0

    def unsigned_text(self, content : str):
        return unidecode(content).lower()


    def _get_current_post_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(By.XPATH, self.POST_XPATH)
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def _get_video_window_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(By.XPATH, value='//div[@aria-label="Close Video and scroll" and @role="button"]')
        except NoSuchElementException:
            logger.error(f"Not found video window")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def _get_current_post_first_element(self) -> Optional[WebElement]:
        self.driver.implicitly_wait(5)
        if not (("/videos/" or "/watch/" or "/reel/" or '/places/')) in self.driver.current_url:
            try:
                post_current_elements = self.driver.find_elements(By.XPATH, self.POST_FIRST_XPATH)
                post_current_element = post_current_elements[-1]
                return post_current_element
            except NoSuchElementException:
                logger.error(f"Not found {self.POST_XPATH}")
                return None
            except Exception as e:
                logger.error(e, exc_info=True)
                return None
        else:
            logger.error("not a post")
            return None
        
    def _get_post_share_element(self, post_element: WebDriver) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return post_element.find_element(By.XPATH, self.POST_SHARE_XPATH)
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_SHARE_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def get_key_subkey(self, keyword_list_raw: str) -> List[str]:
        keyword_list_raw_dict = json.loads(keyword_list_raw)
        keyword_list = []
        subkey_list  = []
        # Lặp qua mỗi dict trong danh sách
        for item in keyword_list_raw_dict:
            item_key = {}
            # Lấy giá trị của key
            key = item['key']
            item_key['key'] = self.unsigned_text(key)
            # Lặp qua mỗi giá trị trong subKey
            for subkey in item['subKey']:
                subkey_list.append(self.unsigned_text(subkey))
                # Thêm từ khóa kết hợp vào danh sách keywords
            item_key['subkey'] = subkey_list
            keyword_list.append(item_key)

        return keyword_list

    def start(self) -> List[Post]:
        # tìm số bài post hiển thị
        post_element_list, post_element_list_size = self._get_current_post_element_list()
        post_element_iterator = PostElementIterator(post_element_list=post_element_list)
        key_unsigned = self.get_key_subkey(self.keyword_noparse)
        while post_element_iterator.index < 20:
            try:  
                post_element = next(post_element_iterator)
                isEnterPost = self._enter_post(post_element)
                if isEnterPost:
                    slept_time = CommonUtils.sleep_random_in_range(1, 5)
                    logger.debug(f"Slept {slept_time}")
                    post_element = self._get_current_post_first_element()
                    if post_element:
                        isEnterGroup = False
                        if "/groups/" in self.driver.current_url:
                            self._enter_post(post_element)
                            if ("/groups/" and "/posts/") in self.driver.current_url:
                                post_element = self._get_current_post_first_element()
                                logger.debug("entered post")
                                isEnterGroup = True

                        post_share_element = self._get_post_share_element(post_element)
                        isPostShare = True if post_share_element else False
                        post_desktop_extractor: PostDesktopExtractor = PostDesktopExtractor(driver=self.driver, post_element=post_element)
                        post = post_desktop_extractor.extract()

                        retry_time = 0
                        def retry_extract(post, retry_time):
                            while not post.is_valid():
                                post_element = self._get_current_post_first_element()
                                post_desktop_extractor: PostDesktopExtractor = PostDesktopExtractor(driver=self.driver, post_element=post_element)
                                post = post_desktop_extractor.extract()
                                if retry_time > 0:
                                    logger.debug(f"Try to extract post {retry_time} times {str(post)}")
                                    slept_time = CommonUtils.sleep_random_in_range(1, 5)
                                    logger.debug(f"Slept {slept_time}")
                                retry_time = retry_time + 1
                                if retry_time > 20:
                                    logger.debug("Retried 20 times, skip post")
                            return
                        retry_extract(post, retry_time)

                        # lọc những bài viết không liên quan đến từ khóa
                        def filter_post(post):
                            logger.debug("-----______----------")
                            contents_unsigned = self.unsigned_text(post.content)
                            for item_key in key_unsigned:
                                if item_key['key'] in contents_unsigned:
                                    for sub_k in item_key['subkey']:
                                        if sub_k in contents_unsigned:
                                            self.posts.append(post)
                                            break
                        filter_post(post)

                        if isPostShare:
                            enter_post = self._enter_post_share(post_share_element)
                            slept_time = CommonUtils.sleep_random_in_range(1, 3)
                            logger.debug(f"Slept {slept_time}")
                            # self.driver.refresh()
                            # self.driver.implicitly_wait(5)
                            post_share_element = self._get_current_post_first_element()
                            
                            if post_share_element:
                                post_share_extractor: PostDesktopExtractor = PostDesktopExtractor(driver=self.driver, post_element=post_share_element)
                                post_share = post_share_extractor.extract()
                                retry_time = 0
                                retry_extract(post_share, retry_time)
                                filter_post(post_share)
                                if enter_post is not None:
                                    self._back()
                                    logger.debug("back when enter post share")
                                    slept_time = CommonUtils.sleep_random_in_range(1, 5)
                                    logger.debug(f"Slept {slept_time}")


                        if isEnterGroup:
                            self._back()
                            logger.debug("back when enter post group")
                            slept_time = CommonUtils.sleep_random_in_range(2, 5)
                            logger.debug(f"Slept {slept_time}")                       


                        if self.callback:
                            self.callback(post)

                    self._back()
                    logger.debug("back to search window")
                    slept_time = CommonUtils.sleep_random_in_range(2, 5)
                    logger.debug(f"Slept {slept_time}")

                video_window_element = self._get_video_window_element()
                if video_window_element:
                    ActionChains(self.driver).move_to_element(video_window_element).click().perform() 

                # self.driver.execute_script("window.scrollBy(0, 400);")

                # self.driver.implicitly_wait(5)
                if post_element_iterator.index == post_element_list_size:
                    self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                    slept_time = CommonUtils.sleep_random_in_range(2, 5)
                    logger.debug(f"Slept {slept_time}")
                    post_element_list, post_element_list_size = self._get_current_post_element_list()
                    post_element_iterator.update(post_element_list=post_element_list)
            except StopIteration as e:
                logger.debug(f"Đã hết post của từ khóa")
                break
        return self.posts

    
    def _enter_post(self, post_element: WebElement):
        logger.info("Start")
        # self.driver.execute_script("arguments[0].scrollIntoView(false);", post_element)
        try:
            a_post_element = post_element.find_elements(By.XPATH, value=".//span[@id and not(@class)]//a")[-1]
            # ActionChains(self.driver).move_to_element(a_post_element).click().perform()
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", a_post_element)
            a_post_element.click()
            logger.info(f"End")
        except NoSuchElementException:
            logger.error(f"Not found xpath enter post ")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        return 1
        

    def _enter_post_share(self, post_element: WebElement):
        logger.info("Start")
        try:
            a_post_content_element = post_element.find_element(By.XPATH, value=".//span[not(@class)]//a[.//span[@aria-labelledby]]")
            ActionChains(self.driver).move_to_element(a_post_content_element).click().perform()
            # self.driver.execute_script("arguments[0].scrollIntoView();", a_post_content_element)
            # a_post_content_element.click()
        except NoSuchElementException:
            logger.error(f"Not found xpath enter post share")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        logger.info(f"End")
        return 1
    
    def _back(self):
        logger.info("Start")
        self.driver.back()
        logger.info("End")


class LinkPostDesktopSearchExtractor:
    driver: WebDriver
    FACEBOOK_SEARCH_LINK: str = "https://www.facebook.com/search/posts?q="
    RECENT_POST_FILTER: str = "&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"
    POST_XPATH: str = './/div[@aria-posinset]'
    LINK_POST_XPATH: str = './/a[contains(@class, "xt0b8zv xo1l8bm") and @tabindex and @role="link" and not(contains(@href, "/user/"))]'
    POST_ID_REGEX_PATTERN = r"(\/posts\/|\/videos\/|\/videos\/\?v=|photo\.php\?fbid=|\/permalink.php\?story_fbid=|multi_permalinks=)([a-zA-Z0-9]+)"
    FACEBOOK_BASE_URL: str = "https://www.facebook.com"
    # LINK_POST_XPATH: str = './/a[contains(@class, "xt0b8zv xo1l8bm") and @tabindex and @role="link"]'

    link_posts: List[Post] = []
    callback: Optional[Callable[[Post], None]] = None

    def __init__(self, driver: WebDriver, keyword: str, share_queue: queue.Queue() ,  callback: Optional[Callable[[Post], None]] = None):
        self.url = f"{self.FACEBOOK_SEARCH_LINK}{keyword}{self.RECENT_POST_FILTER}"
        self.callback = callback
        self.driver = driver
        self.actions = ActionChains(driver)
        self.keyword = keyword
        self.q_posts_group = share_queue
        self.queueLock = threading.Lock()

        try:
            self.link_posts_all = read_data_from_file(path_file=f"db/Search/{self.keyword.replace(' ', '_')}.txt")
            self.link_crawl_done = read_data_from_file(f"db/Search/{self.keyword.replace(' ', '_')}_done.txt")
            
            for link_ in self.link_posts_all:
                if link_ not in self.link_crawl_done:
                    if self.q_posts_group.full():
                        logger.warning("Hàng đợi đã đầy")
                        
                        slept_time = CommonUtils.sleep_random_in_range(1000, 2000)
                        logger.debug(f"Slept {slept_time}")
                        
                    else:
                        self.queueLock.acquire()
                        self.q_posts_group.put(link_)
                        self.queueLock.release()
                    self.link_posts.append(link_)
        except:
            logger.warning(f"File not found {self.keyword.replace(' ', '_')}.txt")
            self.link_posts = []

        self.driver.get(self.url)
        self.driver.implicitly_wait(1000)
        self._scroll()
        slept_time = CommonUtils.sleep_random_in_range(1, 5)
        logger.debug(f"Slept {slept_time}")

    def _scroll(self):
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.driver.implicitly_wait(3)
        except Exception as e:
            logger.error(e)

    def _get_elements_by_xpath(self, XPATH_, parent_element: Optional[WebElement] = None):
        try:
            self.driver.implicitly_wait(1)
            if parent_element is not None:
                return parent_element.find_elements(by=By.XPATH, value=XPATH_)
            return self.driver.find_elements(by=By.XPATH, value=XPATH_)
        except NoSuchElementException as e:
            logger.error(f"Not found {XPATH_}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def _get_element_by_xpath(self, XPATH_, parent_element: Optional[WebElement] = None):
        try:
            self.driver.implicitly_wait(1)
            if parent_element is not None:
                return parent_element.find_element(by=By.XPATH, value=XPATH_)
            return self.driver.find_element(by=By.XPATH, value=XPATH_)
        except NoSuchElementException as e:
            logger.error(f"Not found {XPATH_}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
        
    def start_get_link_posts(self):
        logger.info("get link posts")
        post_element_list = self._get_elements_by_xpath(self.POST_XPATH)
        post_element_iterator = PostElementIterator(post_element_list=post_element_list)
        iDem = 0
        #hàm lấy link bài viết từ các post element
        def _get_link_from_post_element(element):
            #############
            element_link = self._get_element_by_xpath(self.LINK_POST_XPATH, element)
            if element_link:
                # reel ko có link này 
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_link)
            #element_link.click()
                self.actions.move_to_element(element_link).perform()
                CommonUtils.sleep_random_in_range(1,4)
                element_link = self._get_element_by_xpath(self.LINK_POST_XPATH, element)
                link_post = element_link.get_attribute("href")
                time_post = element_link.accessible_name
                logger.warning(time_post)
            ## check xem bài viết quá time hay chưa
           
            return link_post
        
        id_element = 0
        
        check_out = True
        while check_out:
            try:
                element = next(post_element_iterator)
                id_element = post_element_iterator.index
                link_post = _get_link_from_post_element(element=element)
                
                if "/groups/" in link_post:
                    match = re.search(pattern=self.POST_ID_REGEX_PATTERN, string=link_post)
                    if match:
                        post_id = match.group(2)         
                        link_post = f"{self.FACEBOOK_BASE_URL}/{post_id}"

                slept_time = CommonUtils.sleep_random_in_range(3, 5)
                logger.debug(f"Slept {slept_time}")
                if link_post in self.link_posts:
                    # if iDem == 0:
                    #     iDem += 1
                    #     logger.info("Đã lấy hết các bài viết mới.")
                    #     CommonUtils.sleep_random_in_range(3,4)
                    #     continue
                    # elif iDem == 1:
                        # CommonUtils.sleep_random_in_range(3,4)
                        # check_out = False
                    CommonUtils.sleep_random_in_range(2,4)
                self.link_posts.append(link_post)
                
                ##push vào queue
                if self.q_posts_group.full():
                    logger.warning("Hàng đợi đã đầy")
                    slept_time = CommonUtils.sleep_random_in_range(300, 500)
                    logger.debug(f"Slept {slept_time}")
                else:
                    ##ghi vào file để back up
                    write_data_to_file(f"db/Search/{self.keyword.replace(' ', '_')}.txt", str(link_post))
                    self.queueLock.acquire()
                    self.q_posts_group.put(str(link_post))
                    self.queueLock.release()

                # self._scroll()
                if id_element >= (post_element_iterator._len() - 1):
                    slept_time = CommonUtils.sleep_random_in_range(5, 10)
                    logger.debug(f"Slept {slept_time}")
                    post_element_list = self._get_elements_by_xpath(self.POST_XPATH)
                    post_element_iterator.update(post_element_list=post_element_list)
                    logger.info(f"Số bài viết trên giao diện search là {post_element_iterator._len()}")

                if id_element % 20 == 0 and id_element !=0:
                    slept_time = CommonUtils.sleep_random_in_range(60, 120)
                    logger.debug(f"Slept {slept_time}")
            except StopIteration:
                logger.info(f"Đã hết post của trong phần search")
                break


class PostSearchExFromLink():
    driver: WebDriver

    POST_XPATH: str = './/div[@aria-posinset="1"]'
    POST_SHARE_XPATH: str = ".//div[@class='x1y332i5']"
    posts: List[Post] = []
    callback: Optional[Callable[[Post], None]] = None
    post_crawl_done = []
    count_post_ex = 0
    MAX_SIZE_POST = 1000
    
    def __init__(self, driver: WebDriver, keyword: str, keyword_noparse: List ,share_queue: queue.Queue(), callback: Optional[Callable[[Post], None]] = None, ) -> None:
        self.callback = callback
        self.driver = driver
        self.action = ActionChains(driver)
        self.q_posts_group = share_queue
        self.keyword = keyword
        self.keyword_noparse = keyword_noparse
        self.queueLock = threading.Lock()


    def _get_current_post_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(By.XPATH, self.POST_XPATH)
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def _get_post_share_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(By.XPATH, self.POST_SHARE_XPATH)
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_SHARE_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        

    def _enter_post_share(self, post_element: WebElement):
        logger.info("Start")
        try:
            a_post_content_element = post_element.find_element(By.XPATH, value=".//span[not(@class)]//a[contains(@class, 'xt0b8zv xo1l8bm') and @tabindex and @role='link']")
            # ActionChains(self.driver).move_to_element(a_post_content_element).click().perform()
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", a_post_content_element)
            self.action.click(a_post_content_element).perform()
            # a_post_content_element.click()
        except NoSuchElementException:
            logger.error(f"Not found xpath enter post share")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        logger.info(f"End")
        return 1

    def unsigned_text(self, content : str):
        return unidecode(content).lower()
    
    def get_key_subkey(self, keyword_list_raw: str) -> List[str]:
        keyword_list_raw_dict = json.loads(keyword_list_raw)
        keyword_list = []
        subkey_list  = []
        # Lặp qua mỗi dict trong danh sách
        for item in keyword_list_raw_dict:
            item_key = {}
            # Lấy giá trị của key
            key = item['key']
            item_key['key'] = self.unsigned_text(key)
            # Lặp qua mỗi giá trị trong subKey
            for subkey in item['subKey']:
                subkey_list.append(self.unsigned_text(subkey))
                # Thêm từ khóa kết hợp vào danh sách keywords
            item_key['subkey'] = subkey_list
            keyword_list.append(item_key)

        return keyword_list
    
    def start(self):
        bCheck = True
        logger.info("--Start get post search---")
        key_unsigned = self.get_key_subkey(self.keyword_noparse)
        while bCheck:
            try:
                self.queueLock.acquire()
                logger.info(f"Size of queue {self.q_posts_group.qsize()}")
                if self.q_posts_group.empty():
                    self.queueLock.release()
                    slept_time = CommonUtils.sleep_random_in_range(60, 120)
                    logger.debug(f"Slept {slept_time}")
                    continue
                link_post = self.q_posts_group.get()
                self.queueLock.release()

                #ghi link post vào file _done.txt
                write_data_to_file(path_file=f"db/Search/{self.keyword.replace(' ', '_')}_done.txt", message=link_post)

                # link_post = link_post.replace("//www.", "//m.")
                self.driver.get(link_post)
                slept_time = CommonUtils.sleep_random_in_range(2, 5)
                logger.debug(f"Slept {slept_time}")
                post_element = self._get_current_post_element()
                if post_element:
                    post_share_element = self._get_post_share_element()
                    isPostShare = True if post_share_element else False
                    post_extractor: PostDesktopExtractor = PostDesktopExtractor(driver=self.driver, post_element=post_element)
                    post = post_extractor.extract()
                    retry_time = 0
                    def retry_extract(post, retry_time):
                        while not post.is_valid():
                            post = post_extractor.extract()
                            if retry_time > 0:
                                logger.debug(f"Try to extract post {retry_time} times {str(post)}")
                                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                                logger.debug(f"Slept {slept_time}")
                            retry_time = retry_time + 1
                            if retry_time > 1:
                                logger.debug("Retried 20 times, skip post")
                                break
                        return
                    retry_extract(post, retry_time)
                        # lọc những bài viết không liên quan đến từ khóa
                    def filter_post(post):
                        logger.debug("-----______----------")
                        contents_unsigned = self.unsigned_text(post.content)
                        for item_key in key_unsigned:
                            if item_key['key'] in contents_unsigned:
                                for sub_k in item_key['subkey']:
                                    if sub_k in contents_unsigned:
                                        self.posts.append(post)
                                        break
                    filter_post(post)

                    self.posts.append(post)
                    self.count_post_ex += 1

                    if isPostShare:
                        enter_post = self._enter_post_share(post_share_element)
                        self.driver.implicitly_wait(5)
                        self.driver.refresh()
                        slept_time = CommonUtils.sleep_random_in_range(1, 3)
                        logger.debug(f"Slept {slept_time}")

                        post_share_element = self._get_current_post_element()
                        if post_share_element:
                            post_share_extractor: PostDesktopExtractor = PostDesktopExtractor(driver=self.driver, post_element=post_share_element)
                            post_share = post_share_extractor.extract()
                            retry_time = 0
                            retry_extract(post_share, retry_time)
                            filter_post(post_share)

                            self.posts.append(post_share)
                            self.count_post_ex += 1

                            slept_time = CommonUtils.sleep_random_in_range(2, 10)
                            logger.debug(f"Slept {slept_time}")

                    logger.info(f"Số bài viết đã extractor {self.count_post_ex}")

                    if self.callback:
                        self.callback(post)
                    #Check xem số bài viết đã đủ 20 chưa, nếu đủ trả về để đẩy qua kafka
                    if len(self.posts) %20 == 0 and len(self.posts) != 0:
                        yield self.posts
                        self.posts = []
                        slept_time = CommonUtils.sleep_random_in_range(200, 300)
                        logger.debug(f"Slept {slept_time}")
                    #Check xem số bài viết đã vượt giới hạn chưa
                    if self.count_post_ex > self.MAX_SIZE_POST:
                        logger.warning("Đã lấy đủ số lượng bài ưu cầu")
                        break
                
            except Exception as ex:
                logger.error(ex)
                bCheck = False

