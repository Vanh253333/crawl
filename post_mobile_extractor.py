import datetime
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from post_extractor import PostExtractor
from utils.datetime_utils import DatetimeUtils
from utils.log_utils import logger
from utils.string_utils import StringUtils
import json
import re
import time
import traceback
from post_model import Post
from selenium_utils import SeleniumUtils
from utils.common_utils import CommonUtils

class PostMobileExtractor(PostExtractor):
    POST_TIME_XPATH: str = ".//a[\
            (contains(@href, 'https://www.facebook.com') and contains(@href, 'pfbid')) or \
            (contains(@href, 'https://www.facebook.com') and contains(@href, 'groups') and contains(@href, 'multi_permalinks'))\
                ]"
    FACEBOOK_BASE_URL: str = "https://www.facebook.com"
    data_ft: dict = {}
    data_store: dict = {}
    page_insights: dict = {}
    is_entered: bool = False
    POST_PHOTO_XPATH: str = './/i[not(contains(@class, "profpic")) and contains(@class, "img")]'
    POST_PHOTO_XPATH_NOT_LIKE: str = './/i[not(contains(@class, "profpic")) and contains(@class, "img") and not(@role="presentation")]' #xpath không lấy ảnh like
    POST_PROFPIC_XPATH: str = './/i[contains(@class, "profpic") and contains(@class, "img")]'
    POST_COMMENT_AREA_XPATH: str = './/div[contains(@id, ufi_)]'
    POST_COMMENT_XPATH: str = './/div[@data-sigil="comment"]'
    POST_COMMENT_CONTENT_XPATH: str = './/div[@data-sigil="comment-body"]'
    POST_CONTENT_XPATH: str = './/div[@data-gt=\'{"tn":"*s"}\']'
    POST_AUTHOR_AVATAR_IMAGE_XPATH: str = './/div[@data-gt=\'{"tn":"~"}\']//i'
    POST_AUTHOR_XPATH: str = './/h3[//a]//a'
    POST_PHOTO_PLUS: str = '//a[@class="_26ih"]//div[@class="_7om2 _52we _1r5l"]//div[@class="_4g34"]'
    XPATH_IMAGE: str = '//div[@class="_56be"]//div[@class="_i81 _7buy"]//img'
    STYLE_URL_REGEX = r'url\("([^"]+)"\)'
    POST_ID_REGEX_PATTERN = r"(\/posts\/|\/videos\/|\/videos\/\?v=|photo\.php\?fbid=|\/permalink.php\?story_fbid=|multi_permalinks=)([a-zA-Z0-9]+)"
    USER_ID_REGEX_PATTERN = r"^(?:.*)\/(?:pages\/[A-Za-z0-9-]+\/)?(?:profile\.php\?id=)?([A-Za-z0-9.]+)"

    BACK_NAVIGATION_BAR_XPATH: str = '//a[@data-sigil="MBackNavBarClick"]'

    def _get_back_navigation_bar_element(self) -> WebElement:
        return self.driver.find_element(by=By.XPATH, value=self.BACK_NAVIGATION_BAR_XPATH)
    def _back(self):
        logger.info("Start")
        back_navigation_bar_element = self._get_back_navigation_bar_element()
        SeleniumUtils.click_element(driver=self.driver, element=back_navigation_bar_element)
        logger.info("End")
        
    def __init__(self, post_element: WebElement, driver: WebDriver):
        super().__init__(post_element=post_element, driver=driver)
        self._load_metadata()

    def _get_elements_by_xpath(self, XPATH_, parent_element: Optional[WebElement] = None):
        try:
            self.driver.implicitly_wait(1)
            parent_element = parent_element if parent_element else self.post_element
            return parent_element.find_elements(by=By.XPATH, value=XPATH_)
        except NoSuchElementException as e:
            logger.error(f"Not found {XPATH_}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
    def _get_element_by_xpath(self, XPATH_, parent_element: Optional[WebElement] = None):
        try:
            self.driver.implicitly_wait(1)
            parent_element = parent_element if parent_element else self.post_element
            return parent_element.find_element(by=By.XPATH, value=XPATH_)
        except NoSuchElementException as e:
            logger.error(f"Not found {XPATH_}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        
    def _get_photo_element_list(self, parent_element: Optional[WebElement] = None) -> Optional[List[WebElement]]:
        try:
            self.driver.implicitly_wait(1)
            parent_element = parent_element if parent_element else self.post_element
            return parent_element.find_elements(by=By.XPATH, value=self.POST_PHOTO_XPATH_NOT_LIKE)
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_PHOTO_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def _get_comment_area_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(1)
            return self.post_element.find_element(by=By.XPATH, value=self.POST_COMMENT_AREA_XPATH)
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_COMMENT_AREA_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def _get_comment_element_list(self, parent_element: Optional[WebElement] = None) -> Optional[List[WebElement]]:
        try:
            self.driver.implicitly_wait(1)
            parent_element = parent_element if parent_element else self.post_element
            return parent_element.find_elements(by=By.XPATH, value=self.POST_COMMENT_XPATH)
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_COMMENT_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def _get_post_content_element(self) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(1)
            return self.post_element.find_element(by=By.XPATH, value=self.POST_CONTENT_XPATH)
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_CONTENT_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        

    def _load_metadata(self):
        data_ft_str = self.post_element.get_attribute("data-ft")
        if data_ft_str:
            self.data_ft = json.loads(data_ft_str)
            self.page_insights = self.data_ft['page_insights'] if 'page_insights' in self.data_ft else {}

        data_store_str = self.post_element.get_attribute("data-store")
        if data_store_str:
            self.data_store = json.loads(data_store_str)
        

    def get_post_author_element(self) -> Optional[WebElement]:
        logger.info("Start")
        try:
            self.driver.implicitly_wait(1)
            self.post_author_element = self.post_element.find_element(By.XPATH, value=self.POST_AUTHOR_XPATH)
            logger.info("End")
            return self.post_author_element
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_AUTHOR_XPATH}")
        except Exception as e:
            logger.error(e, exc_info=True)

    def extract_post_author(self) -> str:
        logger.info("Start")
        post_author: str = ''
        post_author_element = self.get_post_author_element()
        if post_author_element:
            post_author = post_author_element.text
            logger.info("End")
        else:
            logger.error("Not found post_author_element")
        return post_author

    def extract_post_author_link(self) -> str:
        logger.info("Start")
        post_author_link: str = ''
        post_author_element = self.get_post_author_element()
        if post_author_element:
            post_author_link_full = post_author_element.get_attribute("href")
            post_author_link = StringUtils.regex_match(pattern=self.USER_ID_REGEX_PATTERN, string=post_author_link_full)
            logger.info("End")
        else:
            logger.error("Not found post_author_element")
        return post_author_link

    def extract_post_content(self) -> str: # chưa lấy được content bài search
        logger.info("Start")
        post_content_str: str = ''
        post_content_element = self._get_post_content_element()
        if post_content_element:
            post_content_str = post_content_element.text
            logger.info("End")
        else:
            logger.error("post_content_element None")
        return post_content_str
    
    def _parse_comment(self, comment_element: WebElement) -> dict:
        comment_id = comment_element.get_attribute("id")
        commenter_name: str = ""
        commenter_url: str = ""
        comment_content: str = ""

        profile_picture_element = self._get_profile_picture_element(parent_element=comment_element)
        if profile_picture_element:
            commenter_name = profile_picture_element.get_attribute("alt") or profile_picture_element.get_attribute("aria-label")
            commenter_name = commenter_name.split(",")[0]
            commenter_url = profile_picture_element.find_element(by=By.XPATH, value='..').get_attribute("href")
        else:
            logger.error("Not found profile_picture_element")

        comment_content_element = self._get_comment_content_element(parent_element=comment_element)
        if comment_content_element:
            comment_content = comment_content_element.text
        else:
            logger.error("Not found comment_content_element")

        comment_dict = {
            comment_id: {
                "comment_id": comment_id,
                "commenter_name": commenter_name,
                "commenter_url": commenter_url,
                "comment_content": comment_content,
            }
        }
        return comment_dict

    def _get_comment_content_element(self, parent_element: Optional[WebElement] = None) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(1)
            parent_element = parent_element if parent_element else self.post_element
            return parent_element.find_element(by=By.XPATH, value=self.POST_COMMENT_CONTENT_XPATH)
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_COMMENT_CONTENT_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def _get_profile_picture_element(self, parent_element: Optional[WebElement] = None) -> Optional[WebElement]:
        try:
            self.driver.implicitly_wait(1)
            parent_element = parent_element if parent_element else self.post_element
            return parent_element.find_element(by=By.XPATH, value=self.POST_PROFPIC_XPATH)
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_PROFPIC_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def extract_post_comments(self) -> dict:
        logger.info("Start")
        post_comments: dict = {}
        comment_area_element = self._get_comment_area_element()
        if comment_area_element:
            comment_element_list = self._get_comment_element_list()
            if comment_element_list:
                for comment_element in comment_element_list:
                    comment_dict = self._parse_comment(comment_element=comment_element)
                    post_comments.update(comment_dict)
                logger.info("End")
            else:
                logger.error("Not found comment_element_list")    
        else:
            logger.error("Not found comment_area_element")
        return post_comments

    def extract_post_photos(self) -> dict:
        logger.info("Start")
        post_photos: dict = {}

        #[QUAN] --- lấy hết ảnh trong 1 post
        photo_plus = self._get_element_by_xpath(XPATH_=self.POST_PHOTO_PLUS)
        # if len(photo_plus) == 0:
        #     photo_plus = None
        if photo_plus is not None:
            #img_plus = self._get_element_by_xpath('//a[@class="_26ih"][.//div[@class="_4g34"]]')
            try:
                self.driver.execute_script("arguments[0].click();", photo_plus)
                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                logger.debug(f"Slept {slept_time}")
                check = True
                imgs = {}
                while check:
                    img = self._get_elements_by_xpath(XPATH_=self.XPATH_IMAGE)
                    for photo_element in img:
                        photo_url = photo_element.get_attribute('src')
                        if photo_element.id not in imgs:
                            imgs[photo_element.id] = {"src": photo_url, "alt": photo_element.get_attribute('alt')}

                    # Get current scroll height 
                    original_position  = self.driver.execute_script("return window.pageYOffset;")

                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    self.driver.implicitly_wait(3)


                    new_position = self.driver.execute_script("return window.pageYOffset;")
                    # Calculate difference
                    diff = new_position - original_position
                    if diff <= 0:
                        check = False
                    if check == False:
                        break
                for key, val in imgs.items():
                    photo = {
                            val['src']: val['alt']
                    }
                    post_photos.update(photo)
                self._back()
            except Exception as e:
                logger.error(e)
            return post_photos


        photo_element_list = self._get_photo_element_list()
        if photo_element_list:
            for photo_element in photo_element_list:
                photo_url = photo_element.get_attribute('src')
                if not photo_url:
                    photo_element_style = photo_element.get_attribute('style')
                    if photo_element_style != "":
                        photo_url = StringUtils.regex_extract(pattern=self.STYLE_URL_REGEX, string=photo_element_style)[0]
                photo_description = photo_element.get_attribute('aria-label')
                if photo_url and photo_description:
                    photo = {
                        photo_url: photo_description
                    }
                    post_photos.update(photo)
            logger.info("End")
        else:
            logger.error("Not found photo_element_list")
        return post_photos

    def get_post_time_element(self) -> Optional[WebElement]:
        logger.info("Start")
        if self.post_time_element:
            logger.info(f"End")
            return self.post_time_element
        else:
            self.driver.implicitly_wait(1)
            # NguyenNH: ưu tiên tìm a tag với regex của pfbid:
            try:
                self.post_time_element = self.post_element.find_element(by=By.XPATH, value=self.POST_TIME_XPATH)
                logger.info(f"End")
                return self.post_time_element
            except NoSuchElementException:
                logger.error("Not found a with pfbid, groups and multi_permalinks")
            except Exception as e:
                logger.error(e, exc_info=True)

            # NguyenNH: nếu không có thì tìm a tag với href = # và bên trong có span tag
            try:
                sharp_elements = self.post_element.find_elements(by=By.XPATH, value='.//a[@href="#" and span]')
                for sharp_element in sharp_elements:
                    try:
                        SeleniumUtils.move_to_element(driver=self.driver, element=sharp_element)
                        self.post_time_element = self.post_element.find_element(by=By.XPATH, value=self.POST_TIME_XPATH)
                        return self.post_time_element
                    except NoSuchElementException:
                        logger.error('Not found a with pfbid, groups and multi_permalinks')
                    except Exception as e:
                        logger.error(e, exc_info=True)
            except NoSuchElementException:
                logger.error('Not found .//a[@href="#" and span]')
            except Exception as e:
                logger.error(e, exc_info=True)

            return self.post_time_element

    def extract_post_id(self) -> Optional[str]:
        logger.info("Start")
        if 'top_level_post_id' in self.data_ft:
            post_id = self.data_ft['top_level_post_id']
            logger.info("End")
            return post_id
        else:
            current_url = self.driver.current_url
            match = re.search(pattern=self.POST_ID_REGEX_PATTERN, string=current_url)
            if match:
                post_id = match.group(2)
                logger.info("End")
                return post_id
            else:
                logger.error(f"Not found regex {self.POST_ID_REGEX_PATTERN} in link {current_url}")
        
        


    def extract_post_link(self) -> str:
        logger.info("Start")
        post_link: str = ""
        post_id = self.extract_post_id()
        post_link = f"{self.FACEBOOK_BASE_URL}/{post_id}"
        logger.info("End")
        return post_link
    

    def extract_post_time(self) -> Optional[datetime.datetime]:
        logger.info("Start")
        post_time: Optional[datetime.datetime] = None
        
        # NguyenNH: try to find time in post metadata:
        for page, page_data in self.page_insights.items():
            try:
                publish_time: int = page_data['post_context']['publish_time']
                post_time = DatetimeUtils.from_timestamp(publish_time)
                logger.info("End")
                return post_time
            except (KeyError, ValueError):
                continue
        
        # NguyenNH: try to find time in post:
        try:
            self.driver.implicitly_wait(1)
            abbr_element = self.driver.find_element(by=By.TAG_NAME, value='abbr')
            post_time_str: str = abbr_element.text
            post_time = DatetimeUtils.try_parse_datetime(date_string=post_time_str)
            logger.info("End")
            return post_time
        except NoSuchElementException as e:
            logger.error("Not found element with tagname abbr")
        except Exception as e:
            logger.error(e, exc_info=True)

    
    def extract_post_author_avatar_link(self) -> str:
        logger.info("Start")
        post_author_avatar_link: str = ''
        try:
            self.driver.implicitly_wait(1)
            author_avatar_image_element = self.post_element.find_element(by=By.XPATH, value=self.POST_AUTHOR_AVATAR_IMAGE_XPATH)
            author_avatar_image_element_style = author_avatar_image_element.get_attribute("style")
            post_author_avatar_link = StringUtils.regex_extract(pattern=self.STYLE_URL_REGEX, string=author_avatar_image_element_style)[0]
            logger.info("End")
        except NoSuchElementException:
            logger.error("Not found .//image")
        except:
            traceback.print_exc()
        return post_author_avatar_link
    

    def extract_post_emoji(self):
        pass


    def extract_post_comment(self):
        pass


    def extract_post_share(self):
        pass