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
from time import gmtime, strftime
import calendar
import traceback
from post_model import Post
from selenium_utils import SeleniumUtils
from utils.common_utils import CommonUtils
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta, date

class PostDesktopExtractor(PostExtractor):
    POST_AUTHOR_XPATH: str = ".//h2[@id] | .//h3[@id]"
    POST_TIME_XPATH: str = ".//span[@id and not(@class)]"
    POST_PHOTO_XPATH: str = ".//div[@class='x1n2onr6' and @id]//div[@class='x1n2onr6']//a"
    POST_CONTENT_XPATH: str = ".//div[(@class='' and @dir='auto') or contains(@style, 'background-image')]"
    POST_COMMENT_CONTENT_XPATH: str = ".//div[@role='article' and @aria-label]"
    POST_COMMENT_AREA_XPATH: str = ".//div[@data-visualcompletion='ignore-dynamic' and @class]"
    FACEBOOK_BASE_URL: str = "https://www.facebook.com"
    POST_ID_REGEX_PATTERN = r"(\/posts\/|\/videos\/|\/videos\/\?v=|photo\.php\?fbid=|\/permalink.php\?story_fbid=|multi_permalinks=)([a-zA-Z0-9]+)"
    USER_ID_REGEX_PATTERN = r"^(?:.*)\/(?:pages\/[A-Za-z0-9-]+\/)?(?:profile\.php\?id=)?([A-Za-z0-9.]+)"
    COMMENT_ID_REGEX_PATTERN = r"(?:reply_)?comment_id=(\d+)"

    def __init__(self, post_element: WebElement, driver: WebDriver):
        super().__init__(post_element=post_element, driver=driver)
    
    def _get_elements_by_xpath(self, XPATH_, parent_element: Optional[WebElement] = None):
        try:
            self.driver.implicitly_wait(5)
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


    def _get_post_author_element(self) -> Optional[WebElement]:
        logger.info("Start")
        try:
            self.driver.implicitly_wait(1)
            post_author_element = self.post_element.find_element(By.XPATH, value=self.POST_AUTHOR_XPATH)
            logger.info("End")
            return post_author_element
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_AUTHOR_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    
    def extract_post_author(self):
        logger.info("Start")
        self.post_author: str = ''
        post_author_element = self._get_post_author_element()
        if post_author_element:
            a_author_elements = post_author_element.find_elements(By.XPATH, value=".//a")
            if len(a_author_elements) > 0:
                self.post_author = a_author_elements[0].get_attribute("innerText")
            else:
                self.post_author = "Người tham gia ẩn danh"    
            logger.info("End")
        else:
            logger.error("post_author_element None")
        return self.post_author
    
    def extract_post_author_link(self) -> str:
        logger.info("Start")
        post_author_link: str = ''
        post_author_element = self._get_post_author_element()
        if post_author_element:
            a_author_elements = post_author_element.find_elements(By.XPATH, value=".//a")
            if len(a_author_elements) > 0:
                post_author_link_full = a_author_elements[0].get_attribute("href")
                post_author_link = StringUtils.regex_match(pattern=self.USER_ID_REGEX_PATTERN, string=post_author_link_full) 
            else:
                post_author_link = None
            logger.info("End")
        return post_author_link
        

    def extract_post_author_avatar_link(self) -> str:
        logger.info("start")
        post_author_avatar_link: str = ''
        try:
            self.driver.implicitly_wait(1)
            label = self.post_author.replace("'", "\'")
            author_avatar_element = self.post_element.find_element(by=By.XPATH, value=f'//*[@aria-label="{label}"]')
            author_avatar_image_element = author_avatar_element.find_element(By.TAG_NAME, "image")
            post_author_avatar_link = author_avatar_image_element.get_attribute("xlink:href")
            logger.info("End")
        except NoSuchElementException:
            logger.error(f'Not found //*[@aria-label="{label}"]')
        except:
            traceback.print_exc()
        return post_author_avatar_link
    
    def _get_post_time_element(self) -> Optional[WebElement]:
        logger.info("Start")
        try:
            self.driver.implicitly_wait(1)
            post_time_element = self.post_element.find_element(By.XPATH, value=self.POST_TIME_XPATH)
            logger.info("End")
            return post_time_element
        except NoSuchElementException:
            logger.error(f"Not found {self.POST_TIME_XPATH}")
        except Exception as e:
            logger.error(e, exc_info=True)


    def extract_post_time(self):
        logger.info("Start")
        post_time: str = ''
        post_time_element = self._get_post_time_element()
        if post_time_element:
            try:
                span_post_time_element = post_time_element.find_element(By.XPATH, value=".//span[@style='display: flex;' or @style='display:flex']")
                time_characters = []
                time_character_elements = span_post_time_element.find_elements(By.XPATH, value=".//span")
                for elem in time_character_elements:
                    time_character = elem.text
                    order_value = int(elem.value_of_css_property('order'))
                    position_value = elem.value_of_css_property('position')

                    if position_value == 'relative':
                        time_characters.append({'order_value' : order_value, 'text' : time_character})

                time_characters.sort(key=lambda x: x['order_value'])
                post_time = ''.join(item['text'] for item in time_characters).lower()
                # post_time = getCreatedTime(post_time)
                logger.info("End")
                return post_time
            except NoSuchElementException:
                try:
                    post_time = post_time_element.text
                    logger.info("End")
                    return post_time
                except Exception as e:
                    logger.error(e, exc_info=True)
            except Exception as e:
                logger.error(e, exc_info=True)
        else:
            logger.error("post_time_element None")
    
    def _get_post_content_element(self) -> Optional[WebElement]:
        logger.info("Start")
        try:
            self.driver.implicitly_wait(1)
            post_content_element = self.post_element.find_element(By.XPATH, value=self.POST_CONTENT_XPATH)
            logger.info("End")
            return post_content_element
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_CONTENT_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None


    def extract_post_content(self):
        logger.info("Start")
        post_content_str: str = ''
        post_content_element = self._get_post_content_element()
        if post_content_element:
            try:
                see_more_content_elements = post_content_element.find_elements(By.XPATH, value=".//div[@role='button' and text()='See more']")
                if len(see_more_content_elements) > 0:
                    ActionChains(self.driver).move_to_element(see_more_content_elements[-1]).click().perform()
                    self.driver.implicitly_wait(1)
                    post_content_str = post_content_element.text
                    logger.info("End")
                else:
                    post_content_str = post_content_element.text
                    logger.info("End")
            except Exception as e:
                logger.error(e, exc_info=True)
        else:
            logger.error("post_content_element None")
        return post_content_str
    

    def extract_post_hashtag(self) -> List[str]:
        logger.info("Start")
        hashtag: List[str] = []
        post_content_element = self._get_post_content_element()
        if post_content_element:
            try:
                hashtag_elements = post_content_element.find_elements(By.XPATH, value=".//a[@href[contains(., '/hashtag/')]]")
                for elem in hashtag_elements:
                    hashtag.append(elem.text)
            except NoSuchElementException:
                logger.info("post has no hashtag")
            except Exception as e:
                logger.error(e, exc_info=True)
        else:
            logger.error("post_content_element None")
        return hashtag        


    def extract_post_link(self) -> str:
        logger.info("start")
        post_link: str = ""
        post_id = self.extract_post_id()
        post_link = f"{self.FACEBOOK_BASE_URL}/{post_id}"
        logger.info("End")
        return post_link
        

    def extract_post_id(self) -> Optional[str]:
        logger.info("Start")
        current_url = self.driver.current_url
        match = re.search(pattern=self.POST_ID_REGEX_PATTERN, string=current_url)
        if match:
            post_id = match.group(2)
            logger.info("End")
            return post_id
        else:
            logger.error(f"Not found regex {self.POST_ID_REGEX_PATTERN} in link {current_url}")
        




    def extract_post_photos(self) -> dict:
        logger.info("Start")
        post_photos: dict = {}
        video_links = []

        imgs = self._get_elements_by_xpath(XPATH_=self.POST_PHOTO_XPATH)
        if imgs:
            for img in imgs:
                try:
                    image_element = img.find_element(By.XPATH, value=".//img")
                    image_url = image_element.get_attribute('src')
                    image_alt = image_element.get_attribute('alt')
                    post_photos.update({
                        image_url: image_alt
                    }) 
                except NoSuchElementException:
                    try: 
                        video_element = img.find_element(By.TAG_NAME, value="video")
                        video_link = video_element.get_attribute("src")
                        video_links.append(video_link)
                    except Exception as e:
                        logger.error(e, exc_info=True)                    
                except Exception as e:
                    logger.error(e, exc_info=True)

            photo_plus = imgs[-1].text
            if "+" in photo_plus:
                photo_plus = int(photo_plus.split("+")[-1])
                try:
                    SeleniumUtils.click_element(driver=self.driver, element=imgs[-1])
                    slept_time = CommonUtils.sleep_random_in_range(1, 5)
                    logger.debug(f"Slept {slept_time}")

                    ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                    for i in range(photo_plus-1):
                        slept_time = CommonUtils.sleep_random_in_range(1, 5)
                        logger.debug(f"Slept {slept_time}")
                        try:
                            image_element = self.driver.find_element(By.XPATH, value="//img[@data-visualcompletion]")
                            image_url = image_element.get_attribute('src')
                            image_alt = image_element.get_attribute('alt')
                            post_photos.update({
                                image_url: image_alt
                            }) 
                        except NoSuchElementException:
                            try: 
                                video_element = self.driver.find_element(By.XPATH, value="//a//video")
                                video_link = video_element.get_attribute("src")
                                video_links.append(video_link)
                            except Exception as e:
                                logger.error(e, exc_info=True)  
                        except Exception as e:
                            logger.error(e, exc_info=True)        
                        ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()

                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except Exception as e:
                    logger.error(e)
        logger.info("End")
        return post_photos, video_links


    def _get_comment_area_element(self) -> Optional[WebElement]:
        logger.info("Start")
        try:
            self.driver.implicitly_wait(1)
            comment_area_element = self.post_element.find_element(by=By.XPATH, value=self.POST_COMMENT_AREA_XPATH)
            logger.info("End")
            return comment_area_element
        except NoSuchElementException as e:
            logger.error(f"Not found {self.POST_COMMENT_AREA_XPATH}")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None


    def _parse_comment(self, comment_element: WebElement) -> dict:
        logger.info("Start")
        comment_id: str = ""
        reply_comment_id: str = ""
        commenter_name: str = ""
        commenter_url: str = ""
        comment_content: str = ""
        comment_time_create: str = ""
        comment_icon = []
        comment_img: dict = {}
        comment_video: str = ""
# content
        try:
            # comment_content_element = comment_element.find_element(By.XPATH, value=".//div[@dir='auto' and (@style='text-align: start;' or @style='text-align:start')]")
            comment_content_element = comment_element.find_element(By.XPATH, value=".//span[@dir='auto' and @class]")
            try:
                see_more_element = comment_content_element.find_element(By.XPATH, value=".//div[@role='button' and @class and @tabindex]")
                see_more_element.click()
                self.driver.implicitly_wait(1)
                comment_content = comment_content_element.text
            except NoSuchElementException:
                comment_content = comment_content_element.text
            except Exception as e:
                logger.error(e, exc_info=True)
        except NoSuchElementException:          
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
# thông tin người comment
        commenter_element = comment_element.find_element(By.XPATH, value=".//a[@aria-hidden='false']")
        commenter_name = commenter_element.text
        commenter_url = commenter_element.get_attribute("href")

# ảnhh
        try:
            comment_img_element = comment_element.find_element(By.XPATH, value=".//a//img[@alt and @referrerpolicy]")
            image_url = comment_img_element.get_attribute('src')
            image_alt = comment_img_element.get_attribute('alt')
            comment_img = {
                image_url : image_alt
            }
        except NoSuchElementException:
            logger.info("No image in this comment")
        except Exception as e:
            logger.error(e, exc_info=True)

# video
        try:
            comment_video_element = comment_element.find_element(By.XPATH, value=".//video[@class and @src]")
            comment_video = comment_video_element.get_attribute('src')
        except NoSuchElementException:
            logger.info("No video in this comment")
        except Exception as e:
            logger.error(e, exc_info=True)  

# icon
        try:
            comment_icon_element = comment_element.find_element(By.XPATH, value=".//div[@aria-label[contains(., 'reacted')] and @role='button']")
            SeleniumUtils.click_element(driver=self.driver, element=comment_icon_element)
            self.driver.implicitly_wait(3)
            try:
                reactions_tab_list_element = self.driver.find_element(By.XPATH, value=".//div[@aria-labelledby and @role='dialog']//div[@role='tablist']")
                if reactions_tab_list_element:
                    reactions_tab_elements = reactions_tab_list_element.find_elements(By.XPATH, value=".//div[@role='tab']")[1:]
                    for tab in reactions_tab_elements:
                        reactions = tab.get_attribute('aria-label').lower()
                        comment_icon.append(reactions)
                        # if 'like' in reactions:
                        #     like = reactions.split(",")[1].strip()
                        # elif 'haha' in reactions:
                        #     haha = reactions.split(",")[1].strip()
                        # elif 'wow' in reactions:
                        #     wow = reactions.split(",")[1].strip()
                        # elif 'sad' in reactions:
                        #     sad = reactions.split(",")[1].strip()
                        # elif 'love' in reactions:
                        #     love = reactions.split(",")[1].strip()
                        # elif 'care' in reactions:
                        #     care = reactions.split(",")[1].strip()         
                        # elif 'angry' in reactions:
                        #     angry = reactions.split(",")[1].strip()    

                    # close_element = self.driver.find_element(By.XPATH, value=".//div[@role='button' and @aria-label='Close']")
                    # ActionChains(self.driver).move_to_element(close_element).click().perform()
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    self.driver.implicitly_wait(2)                    
            except Exception as e:
                logger.error(e, exc_info=True)               
        except NoSuchElementException:
            logger.info("No icon in this comment")
        except Exception as e:
            logger.error(e, exc_info=True)
        
        comment_id_element = comment_element.find_element(By.XPATH, ".//ul//a")
        comment_time_create = comment_id_element.text.lower()
        # comment_time_create = getCreatedTime(comment_time_create)
        
        comment_id_url = comment_id_element.get_attribute("href")
        match = re.findall(pattern=self.COMMENT_ID_REGEX_PATTERN, string=comment_id_url)
        if match:
            if (len(match)) == 1:
                comment_id = match[0]
            else:
                comment_id, reply_comment_id = match
        else:
            logger.error(f"Not found regex {self.COMMENT_ID_REGEX_PATTERN} in link {comment_id_url}")
        
        id = reply_comment_id if reply_comment_id !="" else comment_id
        comment_dict = {
            id: {
                "comment_id": comment_id,
                "reply_comment_id": reply_comment_id,
                "commenter_name": commenter_name,
                "commenter_url": commenter_url,
                "comment_content": comment_content,
                "icon" : comment_icon,
                "img" : comment_img,
                "video" : comment_video,
                "tỉme" : comment_time_create
            }
        }
        logger.info("End")
        return comment_dict

    def extract_post_comments(self) -> dict:
        logger.info("start")
        post_comments: dict = {}
        action = ActionChains(self.driver)
        comment_area_element = self._get_comment_area_element()
        if comment_area_element:
            comment_list_size = 0
            while True:
                self.driver.implicitly_wait(3)
                logger.info("crawling comment ..............................................")
                comment_area_element_list = self._get_elements_by_xpath(XPATH_=".//ul//li[not(@class) and not(ancestor::li)]", parent_element=comment_area_element)
                comment_area_element_list = comment_area_element_list[comment_list_size:]

                for comment in comment_area_element_list:
                    action.move_to_element(comment).perform()                    
                    while True:
                        try:
                            repCmt = comment.find_element(By.XPATH, value=".//div[@role='button'][normalize-space(.)!='' and .//i]")
                            action.move_to_element(repCmt).click().perform()
                            self.driver.implicitly_wait(1)
                        except NoSuchElementException:
                            break
                        except Exception as e:
                            logger.error(e, exc_info=True)
                            break
                            
                    comment_content_list = self._get_elements_by_xpath(XPATH_=self.POST_COMMENT_CONTENT_XPATH, parent_element=comment) 
                    for comment in comment_content_list:
                        comment_dic = self._parse_comment(comment_element=comment)
                        post_comments.update(comment_dic)

                comment_area_element_list = self._get_elements_by_xpath(XPATH_=".//ul//li[not(@class) and not(ancestor::li)]", parent_element=comment_area_element)
                comment_list_size = len(comment_area_element_list)

                try:
                    viewMoreCmt = comment_area_element.find_element(By.XPATH, value=".//div[@role='button' and contains(.,'View')]")
                    action.move_to_element(viewMoreCmt).click().perform()
                except NoSuchElementException:
                    logger.info("End")
                    break
        else:
            logger.error("Not found comment_area_element")
        return post_comments


    def reactions_click(self, comment_area_element):
        logger.info("Start")
        try:
            reactions_area_element = comment_area_element.find_element(By.XPATH, value=".//div[@class='x1n2onr6']//span[@aria-label and @role='toolbar']//div[@aria-label]")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reactions_area_element)
            reactions_area_element.click()
            logger.info("End")           
            return 1
        except NoSuchElementException:
            logger.error("Not found reactions_area_element")
            return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def convert_to_number(self,value):
        multipliers = {'k': 1000, 'm': 1000000}
        suffix = value[-1]
        if suffix in multipliers:
            number = float(value[:-1]) * multipliers[suffix]
        else:
            number = float(value)
        return int(number)

    def extract_post_reactions(self) -> List[int]:
        logger.info("Start")
        like = 0
        haha = 0
        wow = 0
        sad = 0
        love = 0
        care = 0
        angry = 0
        comment_area_element = self._get_comment_area_element()
        try:
            # reactions_area_element = comment_area_element.find_element(By.XPATH, value=".//div[@class='x1n2onr6']//span[@aria-label and @role='toolbar']")
            # action = ActionChains(self.driver)
            # action.move_to_element(reactions_area_element).perform()
            # self.driver.implicitly_wait(3)
            # action.click(reactions_area_element).perform()
            click = self.reactions_click(comment_area_element)
            if click:
                slept_time = CommonUtils.sleep_random_in_range(1, 5)
                logger.debug(f"Slept {slept_time}")
                try:
                    self.driver.implicitly_wait(2)
                    reactions_tab_list_element = self.driver.find_element(By.XPATH, value=".//div[@aria-labelledby and @role='dialog']//div[@role='tablist']")
                    if reactions_tab_list_element:
                        reactions_tab_elements = reactions_tab_list_element.find_elements(By.XPATH, value=".//div[@role='tab']")[1:]
                        for tab in reactions_tab_elements:
                            reactions = tab.get_attribute('aria-label').lower()
                            if 'like' in reactions:
                                like = reactions.split(",")[1].strip()
                                like = self.convert_to_number(like)
                            elif 'haha' in reactions:
                                haha = reactions.split(",")[1].strip()
                                haha = self.convert_to_number(haha)
                            elif 'wow' in reactions:
                                wow = reactions.split(",")[1].strip()
                                wow = self.convert_to_number(wow)
                            elif 'sad' in reactions:
                                sad = reactions.split(",")[1].strip()
                                sad = self.convert_to_number(sad)
                            elif 'love' in reactions:
                                love = reactions.split(",")[1].strip()
                                love = self.convert_to_number(love)
                            elif 'care' in reactions:
                                care = reactions.split(",")[1].strip() 
                                care = self.convert_to_number(care)        
                            elif 'angry' in reactions:
                                angry = reactions.split(",")[1].strip() 
                                angry = self.convert_to_number(angry)   

                        close_element = self.driver.find_element(By.XPATH, value=".//div[@role='button' and @aria-label='Close']")
                        ActionChains(self.driver).move_to_element(close_element).click().perform()
                        self.driver.implicitly_wait(2)
                        logger.info("End")                    
                except Exception as e:
                    logger.error(e, exc_info=True)
                # ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

        except NoSuchElementException:
            logger.error(f"Not found reactions_area_element xpath")
        except Exception as e:
            logger.error(e, exc_info=True)
        return like, haha, wow, sad, love, care, angry

    def extract_post_num_of_comment_share(self) -> str:
        logger.info("start")
        num_of_comment = 0
        num_of_share = 0
        comment_area_element = self._get_comment_area_element()
        if comment_area_element:
            try:
                comment_share_area_element = comment_area_element.find_element(By.XPATH, value=".//div[@class='x1n2onr6' and not(ancestor::li)]")
                num_area_elements = comment_share_area_element.find_elements(By.XPATH, value=".//div[@role='button']")
                for elem in num_area_elements:
                    try:
                        i_elem = elem.find_element(By.TAG_NAME, value='i')
                        if "background-position: -51px -126px;" in i_elem.get_attribute("style"):
                            num_of_comment = elem.text
                            num_of_comment = self.convert_to_number(num_of_comment)
                        elif "background-position: -17px -143px;" in i_elem.get_attribute("style"):
                            num_of_share = elem.text
                            num_of_share = self.convert_to_number(num_of_share)
                    except NoSuchElementException:
                        if 'comment' in elem.text:
                            num_of_comment = elem.text.split()[0]
                            num_of_comment = self.convert_to_number(num_of_comment)
                        elif 'share' in elem.text:
                            num_of_share = elem.text.split()[0]      
                            num_of_share = self.convert_to_number(num_of_share)            
                    except Exception as e:
                        logger.error(e, exc_info=True)
                logger.info("End")
            except NoSuchElementException:
                logger.error(f"Not found comment_share_area_element xpath")
            except Exception as e:
                logger.error(e, exc_info=True)
        else:
            logger.error(f"Not found comment_area_element xpath")
        return num_of_comment, num_of_share

