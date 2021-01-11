from time import sleep
from datetime import datetime
import json
import requests
import time
import os
import sys
import subprocess  # For opening a new tab to sound alarm
# https://github.com/mherrmann/selenium-python-helium/blob/master/helium/__init__.py
from helium import *  # Library that makes selenium better
import atexit  # Exit handler to kill browser upon ctrl+c so 50 browsers don't get left opened

# -- data -- #
credentials = json.load(open("credentials.json"))
SCH_EMAIL = credentials["SCH_EMAIL"]
SCH_PASSWORD = credentials["SCH_PASSWORD"]
MAILGUN_URL = credentials["MAILGUN_DOMAIN"]
MAILGUN_API_KEY = credentials["MAILGUN_API_KEY"]
STORE_LIST = credentials["STORE_LIST"]
SCH_BASE_URL = credentials["SCH_BASE_URL"]
STORE = credentials["STORE"]
SCH_DELIVERY_URL = credentials["SCH_DELIVERY_URL"]
NOTIFICATION_EMAILS = credentials["NOTIFICATION_EMAILS"]

DEV_ENVIRONMENT = False

# -- login logic -- #


def login_to_SCH():
    if DEV_ENVIRONMENT == True:
        return None

    print("Logging in...")
    start_chrome(SCH_BASE_URL, headless)
    # sleep(10)
    wait_until(S(f".{STORE}-logo").exists)
    print("Click 'Log In'...")

    if headless:  # Browser opens smaller
        click(S('.mobile-menu-btn'))
        sleep(5)

    click(S('.login-btn'))
    print("Enter login credentials...")
    write(SCH_EMAIL, into="Learner ID")
    write(SCH_PASSWORD, into="password")
    print("Click log in...")
    click(Button("Login"))
    print("Wait for page to load...")
    wait_until(Text("TAY ZHI YING XENIA").exists)


# -- check store logic -- #
def check_delivery_times_for_store():
    print(f"Checking available lessons...")

    keywords_list = [
        "11/Jan/2021",
        "12/Jan/2021",
        "13/Jan/2021",
        "14/Jan/2021",
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
        # Can place mock message here to test out code logic, if logic relies purely on thing.web_element.text
        message = """test"""
    else:
        click(Link("Practical Lesson"))
        wait_until(Text("Select Course").exists)

        option = "-Please Select-"
        print(f"Selecting {option}")

        option = "03. Class 3A Motorcar"
        # option = "Circuit Enhancement Practice (CEP) - Auto" # ALT OPTION FOR TESTING

        print(f"Selecting {option}")
        select(ComboBox('select'), option)
        sleep(5)

        message = S('#aspnetForm > table:nth-child(11) > tbody > tr > td:nth-child(2) > table > tbody > tr:nth-child(2) > td > div > table > tbody > tr:nth-child(3) > td > table').web_element.text

    # if "sessions available" in message: # ALT OPTION FOR TESTING
    if any(word in message for word in keywords_list) and "sessions available" in message:
        lesson_slots = S(
            '#ctl00_ContentPlaceHolder1_gvLatestav').web_element  # only shows up if sessions available

        for session_date in keywords_list:
            # Parses the table row.
            # Available lessons are indicated by <input src=".../Images1.gif">
            inputs = find_all(S("input", to_right_of=session_date))

            for input in inputs:
                input = input.web_element
                src = input.get_attribute('src')

                # THIS IS THE RIGHT OPTION - available lessons
                if src == f"{SCH_BASE_URL}:8080/NewPortal/Images/Class3/Images1.gif":

                    # ALT OPTION FOR TESTING
                    # if src == f"{SCH_BASE_URL}:8080/NewPortal/Images/Class3/Images3.gif":  # confirmed
                    # if src == f"{SCH_BASE_URL}:8080/NewPortal/Images/Class3/Images2.gif":  # reserved
                    # if src == f"{SCH_BASE_URL}:8080/NewPortal/Images/Class3/Images0.gif":  # not available
                    # END ALT OPTION FOR TESTING

                    # Parse out session number from complicated name attr.
                    session_number = input.get_attribute('name').rsplit('$', 1)[
                        1].replace('btnSession', '')
                    timing = sessions[session_number]

                    # get_driver() is Helium's way of using raw selenium.
                    # Execute JS that Helium can't handle.
                    get_driver().execute_script(
                        f"arguments[0].parentElement.append('{timing}')", input)

                    # If camping for a specific day and specific slot.
                    special_date = '14/Jan/2021'
                    if (session_number == "3" or session_number == "4" or session_number == "5") and session_date == special_date:
                        print(
                            f'Session {timing} found for {special_date}, sounding alarm')
                        # subprocess.call(
                        # ['open', 'https://www.youtube.com/watch?v=GWXLPu8Ky9k'])
                        send_simple_message(
                            f'{special_date} {timing}', f"BOOK!")

        # Flush lesson_slots.
        lesson_slots = find_all(S("#ctl00_ContentPlaceHolder1_gvLatestav tr"))

        # Remove <th> for cleaner email preview.
        del lesson_slots[0]

        # Remove verbosity.
        lesson_slots_text = [row.web_element.text.replace(
            '/2021', '') for row in lesson_slots]
        lesson_slots_text = "\n".join(lesson_slots_text)

        return True, lesson_slots_text
    else:
        text = "No lessons found."
        return False, text


# -- format email message -- #
def create_email(messages):
    subject = "Slots found at"

    for message, store in messages:
        subject = f"{subject} {store}"
        text = f"{message}"

    return subject, text


# -- send email -- #
def send_simple_message(subject, text):
    if emailNotification == False:
        print("! ! ! ! ! ! ! ! ! ! ! No email sent, notifications are off. ! ! ! ! ! ! ! ! ! ! !")
        return None

    if (MAILGUN_API_KEY == "") or (MAILGUN_API_KEY == "xxx") or (MAILGUN_URL == "") or (MAILGUN_URL == "xxx.mailgun.org"):
        print("ERROR: Can't sent email notification. Invalid Mailgun API Key, URL or Notification Email")
        return None

    if DEV_ENVIRONMENT == False:
        for to in NOTIFICATION_EMAILS:
            requests.post(
                "https://api.mailgun.net/v3/{}/messages".format(MAILGUN_URL),
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": "SCH Lesson Notifier <SCH_notify@{}>".format(
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
    login_to_SCH()

    message_cache = ""

    if DEV_ENVIRONMENT == True or emailNotification == False:
        print(f"! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! WARNING DEV MODE IS ON OR EMAILS ARE OFF")

    while True:
        print("--------------- " +
              str(datetime.now().strftime("%b %d, %Y %H:%M:%S"))+" ------------")

        lessonAvailability = False
        messages = []

        for store in STORE_LIST:
            availability, message = check_delivery_times_for_store()

            if availability == True:
                messages.append({message: message, store: store})
                lessonAvailability = True
                print(f"Lesson times found for {store}!")

                if message_cache == message:
                    print('No new lessons, skipping email notification')
                    lessonAvailability = False
                else:
                    print(message)
                    message_cache = message
            else:
                print(message)

        if lessonAvailability and emailNotification:
            subject, text = create_email(messages)
            send_simple_message(subject, text)
            # Open Chrome tab to sound alarm.
            # subprocess.call(
            # ['open', 'https://www.youtube.com/watch?v=GWXLPu8Ky9k'])

        print(f"\nNext update in {time_to_wait/60} minute(s)...\n")
        time.sleep(time_to_wait)


@atexit.register
def end():
    # So that we are not left with 50 Chrome browsers lagging up the computer.
    kill_browser()


if __name__ == "__main__":
    # TODO print these and keep them fixed in the top right corner of script
    # -- Start global variables that control the app -- #
    global emailNotification
    global time_to_wait
    global headless
    emailNotification = False
    time_to_wait = 0  # seconds
    headless = False
    # -- End global variables that control the app -- #

    exception = False

    while True:
        try:
            main()
        except Exception as e:
            kill_browser()
            if exception == False:
                # Only executes once in the entire run of the script.
                # Because I bet that an error will either error all the time
                # OR be a one-off and be resolved by the catch().
                send_simple_message('Script Error', f"Error: {e}")
            else:
                print("Script Error, skipping email notification.")

            exception = True
            print(
                f"\nException occured, try again in {time_to_wait/60} minute(s)...\n")
            print(e)
            time.sleep(time_to_wait)
            pass
