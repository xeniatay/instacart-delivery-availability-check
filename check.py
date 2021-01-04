from helium import *
from time import sleep
from datetime import datetime
import json
import requests
import time
import os
import sys

# -- data -- #
credentials = json.load(open("credentials.json"))
CDC_EMAIL = credentials["CDC_EMAIL"]
CDC_PASSWORD = credentials["CDC_PASSWORD"]
MAILGUN_URL = credentials["MAILGUN_DOMAIN"]
MAILGUN_API_KEY = credentials["MAILGUN_API_KEY"]
STORE_LIST = credentials["STORE_LIST"]
CDC_BASE_URL = credentials["CDC_BASE_URL"]
CDC_DELIVERY_URL = credentials["CDC_DELIVERY_URL"]
NOTIFICATION_EMAILS = credentials["NOTIFICATION_EMAILS"]

DEV_ENVIRONMENT = False

# -- login logic -- #


def login_to_CDC():
    if DEV_ENVIRONMENT == True:
        return None

    print("Logging into CDC...")
    start_chrome(CDC_BASE_URL, headless=True)
    # sleep(10)
    wait_until(S(".cdc-logo").exists)
    print("Click 'Log In'...")
    click(S('.mobile-menu-btn'))
    sleep(5)
    click(S('.login-btn'))
    print("Enter login credentials...")
    write(CDC_EMAIL, into="Learner ID")
    write(CDC_PASSWORD, into="password")
    print("Click log in...")
    click(Button("Login"))
    print("Wait for page to load...")
    # idk why but this borked
    wait_until(Text("TAY ZHI YING XENIA").exists)
    # sleep(5)


# -- check store logic -- #
def check_delivery_times_for_store():
    print(f"Checking available lessons...")

    keywords_list = [
        "9 Jan 2021",
        "10 Jan 2021",
        "11 Jan 2021",
        "12 Jan 2021",
        "13 Jan 2021",
        "14 Jan 2021",
        "09/Jan/2021",
        "10/Jan/2021",
        "11/Jan/2021",
        "12/Jan/2021",
        "13/Jan/2021",
        "14/Jan/2021",
        "session available"
    ]

    sessions = {
        "1": "08:30 - 10:10",
        "2": "10:20 - 12:00",
        "3": "12:45 - 14:25",
        "4": "14:35 - 16:15",
        "5": "16:25 - 18:05",
        "6": "18:50 - 20:30",
        "7": "20:40 - 22:20"
    }

    if DEV_ENVIRONMENT == True:
        message = """test"""
    else:
        click(Link("Practical Lesson"))
        wait_until(Text("Select Course").exists)

        option = "-Please Select-"
        print(f"Selecting {option}")

        option = "03. Class 3A Motorcar"
        # option = "Circuit Enhancement Practice (CEP) - Auto"

        print(f"Selecting {option}")
        select(ComboBox('select'), option)
        sleep(5)

        message = S('#aspnetForm > table:nth-child(11) > tbody > tr > td:nth-child(2) > table > tbody > tr:nth-child(2) > td > div > table > tbody > tr:nth-child(3) > td > table').web_element.text

    if any(word in message for word in keywords_list) and "sessions available" in message:
    # if "sessions available" in message:
        lesson_slots = S('#ctl00_ContentPlaceHolder1_gvLatestav').web_element
        get_driver().execute_script(
            "arguments[0].querySelector('tbody > tr:nth-child(1)').remove()", lesson_slots)

        for input in lesson_slots.find_elements_by_tag_name('input'):
            src = input.get_attribute('src')
            get_driver().execute_script(
                "arguments[0].setAttribute('type', 'button')", input)

            if src == "https://www.cdc.com.sg:8080/NewPortal/Images/Class3/Images0.gif":
                get_driver().execute_script(
                    "arguments[0].remove()", input)
            elif src == "https://www.cdc.com.sg:8080/NewPortal/Images/Class3/Images1.gif":
                session_number = input.get_attribute('name').rsplit('$', 1)[
                    1].replace('btnSession', '')
                get_driver().execute_script(
                    f"arguments[0].append('{sessions[session_number]}')", input)

        # Flush variable
        lesson_slots = S('#ctl00_ContentPlaceHolder1_gvLatestav').web_element
        lesson_slots_text = lesson_slots.text.replace('/2021', '')

        return True, lesson_slots_text, lesson_slots_text
    else:
        return False, "No lessons found.", "No lessons found."


# -- format email message -- #
def create_email(messages):
    subject = "Lesson times found at"

    for message, store in messages:
        subject = f"{subject} {store}"
        text = f"{message}"

    return subject, text


# -- send email -- #
def send_simple_message(subject, text):

    if (MAILGUN_API_KEY == "") or (MAILGUN_API_KEY == "xxx") or (MAILGUN_URL == "") or (MAILGUN_URL == "xxx.mailgun.org"):
        print("ERROR: Can't sent email notification. Invalid Mailgun API Key, URL or Notification Email")
        return None

    if DEV_ENVIRONMENT == False:
        for to in NOTIFICATION_EMAILS:
            requests.post(
                "https://api.mailgun.net/v3/{}/messages".format(MAILGUN_URL),
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": "CDC Lesson Notifier <CDC_notify@{}>".format(
                        MAILGUN_URL
                    ),
                    "to": to,
                    "subject": subject,
                    "text": text,
                    # "html": text,
                },
            )
            print(f"'{subject}' email sent to {to}")

    return None

# -- check all stores in list and notify -- #


def main():
    login_to_CDC()

    emailNotification = True
    message_cache = ""
    time_to_wait = 30  # seconds
    exception = False

    if DEV_ENVIRONMENT == True or emailNotification == False:
        print(f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! WARNING DEV MODE IS ON OR EMAILS ARE OFF")

    while True:
        print("--------------- " +
              str(datetime.now().strftime("%b %d, %Y %H:%M:%S"))+" ------------")

        try:
            lessonAvailability = False
            messages = []

            for store in STORE_LIST:
                availability, message, message_plain_text = check_delivery_times_for_store()

                if availability == True:
                    messages.append({message: message, store: store})
                    lessonAvailability = True
                    print(f"Lesson times found for {store}!")

                    if message_cache == message:
                        print('No new lessons, skipping email notification')
                        lessonAvailability = False
                    else:
                        print(message_plain_text)
                        message_cache = message
                else:
                    print(message_plain_text)

            if lessonAvailability and emailNotification:
                subject, text = create_email(messages)
                send_simple_message(subject, text)

            print(f"\nNext update in {time_to_wait/60} minute(s)...\n")
            time.sleep(time_to_wait)
        except Exception as e:
            if exception == False: 
                send_simple_message('Script Error', e)
            else: 
                print("Script Error, skipping email notification.")

            exception = True
            print(
                f"\nException occured, try again in {time_to_wait/60} minute(s)...\n")
            print(e)
            time.sleep(time_to_wait)
            pass


if __name__ == "__main__":
    main()
