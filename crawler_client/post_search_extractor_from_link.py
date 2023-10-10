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
from post_search_extractor import PostElementIterator
from utils.utils import write_data_to_file, read_data_from_file

class PostsDesktopGroupExtractor:
    driver: WebDriver
    GROUP_FACEBOOK_DESKTOP: str = "https://www.facebook.com/groups/"
    POST_XPATH: str = "//div[@aria-posinset and @aria-describedby]"
    LINK_POST_XPATH: str = './/a[contains(@class, "xt0b8zv xo1l8bm") and @tabindex and @role="link"]'

    link_posts: List[Post] = []
    callback: Optional[Callable[[Post], None]] = None
    def __init__(self, driver: WebDriver, group_id : str, callback: Optional[Callable[[Post], None]] = None) -> None:
        self.group_id = group_id
        self.group_link = self.GROUP_FACEBOOK_DESKTOP + group_id + "?sorting_setting=CHRONOLOGICAL"
        self.callback = callback
        self.driver = driver
        self.actions = ActionChains(driver)
        # self.q_posts_group = share_queue
        # self.queueLock = threading.Lock()
        try:
            self.link_posts_all = read_data_from_file(path_file=f"db/Groups/{group_id}.txt")
            self.link_crawl_done = read_data_from_file(f"db/Groups/{group_id}_done.txt")
            
            for link_ in self.link_posts_all:
                if link_ not in self.link_crawl_done:
                    # if self.q_posts_group.full():
                    #     logger.warning("Hàng đợi đã đầy")
                        
                    #     slept_time = CommonUtils.sleep_random_in_range(1000, 2000)
                    #     logger.debug(f"Slept {slept_time}")
                        
                    # else:
                    #     self.queueLock.acquire()
                    #     self.q_posts_group.put(link_)
                    #     self.queueLock.release()
                    self.link_posts.append(link_)
        except:
            logger.warning(f"File not found {group_id}.txt")
            self.link_posts = []

        self.driver.get(self.group_link)
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
        logger.warning("get link posts")
        post_element_list = self._get_elements_by_xpath(self.POST_XPATH)
        post_element_iterator = PostElementIterator(post_element_list=post_element_list)
        iDem = 0
        #hàm lấy link bài viết từ các post element
        def _get_link_from_post_element(element):
            #############
            element_link = self._get_element_by_xpath(self.LINK_POST_XPATH, element)
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_link)
            #element_link.click()
            self.actions.move_to_element(element_link).perform()
            CommonUtils.sleep_random_in_range(1,4)
            element_link = self._get_element_by_xpath(self.LINK_POST_XPATH, element)
            link_post = element_link.get_attribute("href")
            time_post = element_link.accessible_name
            ## check xem bài viết quá time hay chưa
           
            return link_post
        
        id_element = 0
        
        check_out = True
        while check_out:
            try:
                element = next(post_element_iterator)
                id_element = post_element_iterator.index
                link_post = _get_link_from_post_element(element=element)
                slept_time = CommonUtils.sleep_random_in_range(3, 7)
                logger.debug(f"Slept {slept_time}")
                # if link_post in self.link_posts:
                    # if iDem == 0:
                    #     iDem += 1
                    #     logger.info("Đã lấy hết các bài viết mới.")
                    #     CommonUtils.sleep_random_in_range(3,4)
                    #     continue
                    # elif iDem == 1:
                        # CommonUtils.sleep_random_in_range(3,4)
                        # check_out = False
                    # CommonUtils.sleep_random_in_range(2,4)
                self.link_posts.append(link_post)
                
                ##push vào queue
                # if self.q_posts_group.full():
                #     logger.warning("Hàng đợi đã đầy")
                #     slept_time = CommonUtils.sleep_random_in_range(300, 500)
                #     logger.debug(f"Slept {slept_time}")
                # else:
                    ##ghi vào file để back up
                write_data_to_file(f"db/Groups/{self.group_id}.txt", str(link_post))
                    # self.queueLock.acquire()
                    # self.q_posts_group.put(str(link_post))
                    # self.queueLock.release()

                # self._scroll()
                if id_element >= (post_element_iterator._len() - 1):
                    slept_time = CommonUtils.sleep_random_in_range(5, 10)
                    logger.debug(f"Slept {slept_time}")
                    post_element_list = self._get_elements_by_xpath(self.POST_XPATH)
                    post_element_iterator.update(post_element_list=post_element_list)
                    logger.info(f"Số bài viết trên giao diện group là {post_element_iterator._len()}")

                if id_element % 20 == 0 and id_element !=0:
                    slept_time = CommonUtils.sleep_random_in_range(60, 120)
                    logger.debug(f"Slept {slept_time}")
            except StopIteration as e:
                logger.info(f"Đã hết post của trong group")
                break