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
INSTACART_EMAIL = credentials["INSTACART_EMAIL"]
INSTACART_PASSWORD = credentials["INSTACART_PASSWORD"]
MAILGUN_URL = credentials["MAILGUN_DOMAIN"]
MAILGUN_API_KEY = credentials["MAILGUN_API_KEY"]
STORE_LIST = credentials["STORE_LIST"]
INSTACART_BASE_URL = credentials["INSTACART_BASE_URL"]
INSTACART_DELIVERY_URL = credentials["INSTACART_DELIVERY_URL"]
NOTIFICATION_EMAILS = credentials["NOTIFICATION_EMAILS"]

DEV_ENVIRONMENT = False

# -- login logic -- #
def login_to_instacart():
    if DEV_ENVIRONMENT == True:
        return None

    print("Logging into Instacart...")
    start_chrome(INSTACART_BASE_URL, headless=True)
    print("Click 'Log In'...")
    click(Button("Log In"))
    print("Enter login credentials...")
    write(INSTACART_EMAIL, into="email")
    write(INSTACART_PASSWORD, into="password")
    print("Click log in...")
    click(Button("Log In"))
    print("Wait for page to load...")
    # idk why but this borked
    # wait_until(Text("Your Items").exists)
    sleep(5)


# -- check store logic -- #
def check_delivery_times_for_store(store_name):
    print(f"Checking available delivery slots for {store_name}...")

    if DEV_ENVIRONMENT == True:
        message = """
            Prices listed for orders $35 and above per store. Demand is higher than normal. When you choose "Fast & Flexible", your order will be taken once a shopper is available.
            Fast & Flexible
            Apr 17 - Apr 18
            FREE
            Sunday, April 19
            9am - 11am
            FREE
            Wednesday, April 22
            1pm - 3pm
            FREE
            2pm - 4pm
            FREE
            3pm - 5pm
            FREE
            More times
        """
    else: 
        go_to(INSTACART_DELIVERY_URL.format(store_name))
        sleep(5)
        message = S('#react-tabs-1').web_element.text

    keywords_list = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "Today", 
        "Tomorrow",
        "More Times"
    ]

    if any(word in message for word in keywords_list) and 'am - ' in message: 
        return True, message
    elif "There was a problem loading this page" in message:
        return False, "There was a problem loading {}".format(store_name)
    elif "No delivery times available" in message:
        return False, "No Delivery times available for {}".format(store_name)
    else:
        return False, "No ideal delivery times found."

# -- format email message -- #
def create_email(messages):
    subject = "Delivery times found at"
    text = ""

    for message, store in messages:
        subject = f"{subject} {store}"
        text = f"{text}\n{store}: {message}"

    return subject, text


# -- send email -- #
def send_simple_message(subject, text):

    if (MAILGUN_API_KEY=="") or (MAILGUN_API_KEY=="xxx") or (MAILGUN_URL=="") or (MAILGUN_URL=="xxx.mailgun.org"):
        print ("ERROR: Can't sent email notification. Invalid Mailgun API Key, URL or Notification Email")
        return None

    if DEV_ENVIRONMENT == False:
        for to in NOTIFICATION_EMAILS:
            requests.post(
                "https://api.mailgun.net/v3/{}/messages".format(MAILGUN_URL),
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": "Instacart Delivery Notifier <instacart_notify@{}>".format(
                        MAILGUN_URL
                    ),
                    "to": to,
                    "subject": subject,
                    "text": text,
                },
            )
            print (f"'{subject}' email sent to {to}")

    return None

# -- check all stores in list and notify -- #
def main():
    login_to_instacart()

    emailNotification = True

    while True: 
        print("--------------- "+str(datetime.now().strftime("%b %d, %Y %H:%M:%S"))+" ------------")

        deliveryAvailability = False
        messages = []

        for store in STORE_LIST:
            availability, message = check_delivery_times_for_store(store)
            print(message)
            if availability == True:
                messages.append({message: message, store: store})
                deliveryAvailability = True

        if deliveryAvailability and emailNotification:
            subject, text = create_email(messages)
            send_simple_message(subject,text)

        if deliveryAvailability:
            print("\nNext update in 1 hour...\n")
            time.sleep(3600)
        else:
            print("\nNext update in 15 minutes...\n")
            time.sleep(900)


if __name__ == "__main__":
    main()
