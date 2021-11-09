import time, random, os, csv, platform
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import pyautogui

from urllib.request import urlopen
from webdriver_manager.chrome import ChromeDriverManager
import re
import yaml
from datetime import datetime, timedelta

import random

log = logging.getLogger(__name__)
driver = webdriver.Chrome(ChromeDriverManager().install())


def setupLogger():
    dt = datetime.strftime(datetime.now(), "%m_%d_%y %H_%M_%S ")

    if not os.path.isdir('./logs'):
        os.mkdir('./logs')

    # TODO need to check if there is a log dir available or not
    logging.basicConfig(filename=('./logs/' + str(dt) + 'applyJobs.log'), filemode='w',
                        format='%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='./logs/%d-%b-%y %H:%M:%S')
    log.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)


class EasyApplyBot:
    setupLogger()
    # MAX_SEARCH_TIME is 10 hours by default, feel free to modify it
    MAX_SEARCH_TIME = 10 * 60 * 60

    def __init__(self,
                 username,
                 password,
                 uploads={},
                 filename='output.csv',
                 blacklist=[],
                 blackListTitles=[]):

        log.info("Welcome to Easy Apply Bot")
        dirpath = os.getcwd()
        log.info("current directory is : " + dirpath)

        self.uploads = uploads
        past_ids = self.get_appliedIDs(filename)
        self.appliedJobIDs = past_ids if past_ids != None else []
        self.filename = filename
        self.options = self.browser_options()
        self.browser = driver
        self.wait = WebDriverWait(self.browser, 30)
        self.blacklist = blacklist
        self.blackListTitles = blackListTitles
        # self.start_linkedin(username, password)
        self.username = username
        self.password = password
        self.jobIDs_forApplication = []
        self.jobIDs_surveyed = []

    def get_appliedIDs(self, filename):
        try:
            df = pd.read_csv(filename,
                             header=None,
                             names=['timestamp', 'jobID', 'job', 'company', 'attempted', 'result'],
                             lineterminator='\n',
                             encoding='utf-8')

            df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
            df = df[df['timestamp'] > (datetime.now() - timedelta(days=2))]
            jobIDs = list(df.jobID)
            log.info(f"{len(jobIDs)} jobIDs found")
            return jobIDs
        except Exception as e:
            log.info(str(e) + "   jobIDs could not be loaded from CSV {}".format(filename))
            print('no job satisying specification can be found. pls modify your requirements')
            return None

    def browser_options(self):
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-extensions")

        # Disable webdriver flags or you will be easily detectable
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options

    def start_linkedin(self, username, password):
        log.info("Logging in.....Please wait :)  ")
        self.browser.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        try:
            user_field = self.browser.find_element_by_id("username")
            pw_field = self.browser.find_element_by_id("password")
            login_button = self.browser.find_element_by_css_selector(".btn__primary--large")
            user_field.send_keys(username)
            user_field.send_keys(Keys.TAB)
            time.sleep(2)
            pw_field.send_keys(password)
            time.sleep(2)
            login_button.click()
            time.sleep(3)
        except TimeoutException:
            log.info("TimeoutException! Username/password field or login button not found")
        print('cannot log into LinkedIn. pls make sure you disallow 2-factor verification and give system permission to python.')

    def fill_data(self):
        self.browser.set_window_size(0, 0)
        self.browser.set_window_position(2000, 2000)

    def start_apply(self, positions, locations):
        start = time.time()
        self.fill_data()

        combos = []
        while len(combos) < len(positions) * len(locations):
            position = positions[random.randint(0, len(positions) - 1)]
            location = locations[random.randint(0, len(locations) - 1)]
            combo = (position, location)
            if combo not in combos:
                combos.append(combo)
                # log.info(f"Applying to {position}: {location}")
                # location = "&location=" + location
                # self.applications_loop(position, location)
            if len(combos) > 500:
                break

        for combo in combos:
            # write down all viable job application IDs
            count_application = 0
            jobs_per_page = 0
            start_time = time.time()

            log.info("Looking for jobs.. Please wait..")
            # one needs to log into LinkedIn with any profile to be able to find jobs
            self.start_linkedin[self.username[0], self.password[0]]

            self.browser.set_window_position(0, 0)
            self.browser.maximize_window()
            self.browser, _ = self.next_jobs_page(combo[0], combo[1], jobs_per_page)
            log.info("Looking for jobs.. Please wait..")

            while time.time() - start_time < self.MAX_SEARCH_TIME:
                try:
                    log.info(f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search")

                    # sleep to make sure everything loads, add random to make us look human.
                    randoTime = random.uniform(3.5, 4.9)
                    log.debug(f"Sleeping for {round(randoTime, 1)}")
                    time.sleep(randoTime)
                    self.load_page(sleep=1)

                    # LinkedIn displays the search results in a scrollable <div> on the left side, we have to scroll to its bottom

                    scrollresults = self.browser.find_element_by_class_name(
                        "jobs-search-results"
                    )
                    # Selenium only detects visible elements; if we scroll to the bottom too fast, only 8-9 results will be loaded into IDs list
                    for i in range(300, 3000, 100):
                        self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollresults)

                    time.sleep(1)

                    # get job links
                    links = self.browser.find_elements_by_xpath(
                        '//div[@data-job-id]'
                    )

                    if len(links) == 0:
                        break

                    # get job ID of each job link
                    IDs = []
                    for link in links:
                        children = link.find_elements_by_xpath(
                            './/a[@data-control-name]'
                        )
                        for child in children:
                            if child.text not in self.blacklist:
                                temp = link.get_attribute("data-job-id")
                                jobID = temp.split(":")[-1]
                                IDs.append(int(jobID))
                    IDs = set(IDs)

                    # remove already applied jobs and already registered jobs
                    before = len(IDs)
                    jobIDs = [x for x in IDs if x not in self.appliedJobIDs and x not in self.jobIDs_surveyed]
                    self.jobIDs_surveyed = self.jobIDs_surveyed + jobIDs
                    after = len(jobIDs)

                    # it assumed that 25 jobs are listed in the results window
                    if len(jobIDs) == 0 and len(IDs) > 23:
                        jobs_per_page = jobs_per_page + 25
                        count_job = 0
                        self.avoid_lock()
                        self.browser, jobs_per_page = self.next_jobs_page(combo[0],
                                                                        combo[1],
                                                                        jobs_per_page)

        # remove job IDs without LinkedIn easy apply button
        for i, jobID in enumerate(self.jobIDs_surveyed):
            self.get_job_page(jobID)
            button = self.get_easy_apply_button()
            if button is not False:
                if any(word in self.browser.title for word in blackListTitles):
                    log.info('skipping this application, a blacklisted keyword was found in the job position: ' + jobID)
                else:
                    self.jobIDs_forApplication.append(jobID)

        # divide the job application IDs randomly between all profiles
        random.shuffle(self.jobIDs_forApplication)

        # application with each profile
        n_profiles = len(self.username)
        n_applications = 0
        for i in range(n_profiles):
            username = self.username[i]
            password = self.password[i]
            resume = self.uploads['Resume'][i]
            cover_letter = self.uploads['Cover Letter'][i]


            self.start_linkedin(username, password)
            # job IDs for its application
            n_jobs_profile_application = int(len(self.jobIDs_forApplication)/n_profiles)
            jobIDs_profile_application = self.jobIDs_forApplication[i * n_jobs_profile_application : (i + 1) * n_jobs_profile_application]

            for i_jobID, jobID in enumerate(jobIDs_profile_application):
                self.get_job_page(jobID)
                button = self.get_easy_apply_button()

                if button is False:
                    log.info('After filtering for jobs with no Easy Apply, job ' + jobID + ' still does not have easy apply button')
                else:
                    log.info('Clicking easy apply button for job: ' + jobID)
                    button.click()
                    time.sleep(3)
                    result = self.send_resume(i)
                    n_applications += 1
                    self.write_to_file(button, jobID, self.browser.title, result)

                    if n_applications != 0 and n_applications % 20 == 0:
                        sleepTime = random.randint(500, 900)
                        log.info(f"""********count_application: {count_application}************\n\n
                                    Time for a nap - see you in:{int(sleepTime / 60)} min
                                ****************************************\n\n""")
                        time.sleep(sleepTime)


    # self.finish_apply() --> this does seem to cause more harm than good, since it closes the browser which we usually don't want, other conditions will stop the loop and just break out

    

    def write_to_file(self, button, jobID, browserTitle, result):
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attempted = False if button == False else True
        job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")

        toWrite = [timestamp, jobID, job, company, attempted, result]
        with open(self.filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    def get_job_page(self, jobID):

        job = 'https://www.linkedin.com/jobs/view/' + str(jobID)
        self.browser.get(job)
        self.job_page = self.load_page(sleep=0.5)
        return self.job_page

    def get_easy_apply_button(self):
        try:
            button = self.browser.find_elements_by_xpath(
                '//button[contains(@class, "jobs-apply")]/span[1]'
            )

            EasyApplyButton = button[0]
        except:
            EasyApplyButton = False

        return EasyApplyButton

    def send_resume(self, i_profile):
        def is_present(button_locator):
            return len(self.browser.find_elements(button_locator[0],
                                                  button_locator[1])) > 0

        try:
            time.sleep(random.uniform(1.5, 2.5))
            next_locater = (By.CSS_SELECTOR,
                            "button[aria-label='Continue to next step']")
            review_locater = (By.CSS_SELECTOR,
                              "button[aria-label='Review your application']")
            submit_locater = (By.CSS_SELECTOR,
                              "button[aria-label='Submit application']")
            submit_application_locator = (By.CSS_SELECTOR,
                                          "button[aria-label='Submit application']")
            error_locator = (By.CSS_SELECTOR,
                             "p[data-test-form-element-error-message='true']")
            upload_locator = (By.CSS_SELECTOR, "input[name='file']")
            follow_locator = (By.CSS_SELECTOR, "label[for='follow-company-checkbox']")

            submitted = False
            while True:

                # Upload Cover Letter if possible
                if is_present(upload_locator):

                    input_buttons = self.browser.find_elements(upload_locator[0],
                                                               upload_locator[1])
                    for input_button in input_buttons:
                        parent = input_button.find_element(By.XPATH, "..")
                        sibling = parent.find_element(By.XPATH, "preceding-sibling::*")
                        grandparent = sibling.find_element(By.XPATH, "..")
                        for key in self.uploads.keys():
                            sibling_text = sibling.text
                            gparent_text = grandparent.text
                            if key.lower() in sibling_text.lower() or key in gparent_text.lower():
                                input_button.send_keys(self.uploads[key][i])

                    # input_button[0].send_keys(self.cover_letter_loctn)
                    time.sleep(random.uniform(4.5, 6.5))

                # Click Next or submitt button if possible
                button = None
                buttons = [next_locater, review_locater, follow_locator,
                           submit_locater, submit_application_locator]
                for i, button_locator in enumerate(buttons):
                    if is_present(button_locator):
                        button = self.wait.until(EC.element_to_be_clickable(button_locator))

                    if is_present(error_locator):
                        for element in self.browser.find_elements(error_locator[0],
                                                                  error_locator[1]):
                            text = element.text
                            if "Please enter a valid answer" in text:
                                button = None
                                break
                    if button:
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))
                        if i in (3, 4):
                            submitted = True
                        if i != 2:
                            break
                if button == None:
                    log.info("Could not complete submission")
                    break
                elif submitted:
                    log.info("Application Submitted")
                    break

            time.sleep(random.uniform(1.5, 2.5))


        except Exception as e:
            log.info(e)
            log.info("cannot apply to this job")
            raise (e)

        return submitted

    def load_page(self, sleep=1):
        scroll_page = 0
        while scroll_page < 4000:
            self.browser.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 200
            time.sleep(sleep)

        if sleep != 1:
            self.browser.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        page = BeautifulSoup(self.browser.page_source, "lxml")
        return page

    def avoid_lock(self):
        x, _ = pyautogui.position()
        pyautogui.moveTo(x + 200, pyautogui.position().y, duration=1.0)
        pyautogui.moveTo(x, pyautogui.position().y, duration=0.5)
        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(0.5)
        pyautogui.press('esc')

    def next_jobs_page(self, position, location, jobs_per_page):
        self.browser.get(
            "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=" +
            position + location + "&start=" + str(jobs_per_page))
        self.avoid_lock()
        log.info("Lock avoided.")
        self.load_page()
        return (self.browser, jobs_per_page)

    def finish_apply(self):
        self.browser.close()


if __name__ == '__main__':

    with open("config_modified.yaml", 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert len(parameters['username']) > 0
    assert len(parameters['password']) > 0
    assert len(parameters['username']) == len(parameters['password'])


    output_filename = [f for f in parameters.get('output_filename', ['output.csv']) if f != None]
    output_filename = output_filename[0] if len(output_filename) > 0 else 'output.csv'
    blacklist = parameters.get('blacklist', [])
    blackListTitles = parameters.get('blackListTitles', [])

    uploads = {} if parameters.get('uploads', {}) == None else parameters.get('uploads', {})
    for key in uploads.keys():
        assert len(uploads[key]) > 0

    bot = EasyApplyBot(parameters['username'],
                       parameters['password'],
                       uploads=uploads,
                       filename=output_filename,
                       blacklist=blacklist,
                       blackListTitles=blackListTitles
                       )

    locations = [l for l in parameters['locations'] if l != None]
    positions = [p for p in parameters['positions'] if p != None]
    bot.start_apply(positions, locations)
    print('job done')
