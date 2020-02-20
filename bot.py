import requests
import slack
import os
from bs4 import BeautifulSoup
from datetime import datetime

CHANNEL = "#bounty-hunter"
BUGCROWD_URL = "https://bugcrowd.com/crowdstream?page={page}"
TOKEN = os.environ['SLACK_API_TOKEN']


def get_bc_items(page):
    issues = []
    url = BUGCROWD_URL.format(page=page)
    page = requests.get(url)
    if page.status_code == 200:
        soup = BeautifulSoup(page.text, 'html.parser')
        ul = soup.find("ul", class_="bc-list")
        for li in ul.findAll('li'):
            dttag = li.find("span", class_="bc-crowdstream-item__date")
            if dttag:
                dt = dttag.find("time")["datetime"]
                dtobj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%SZ')  # 2020-02-19T05:56:30Z
                diff = datetime.utcnow() - dtobj

                if diff.days == 1:
                    #issues.append({"link":link, "title": title, "foundby": foundby, "vendor": vendor, "bounty": bounty, "severity": severity, "image": image})
                    i = {"link": None, "title": None, "foundby": None,
                         "vendor": None, "bounty": None, "severity": None, "image": None}

                    if li.find("span", class_="bc-reward") is not None:
                        i["bounty"] = li.find("span", class_="bc-reward").text

                    if li.find("span", class_="bc-badge") is not None:
                        i["severity"] = li.find("span", class_="bc-badge").text.replace("\n", "")

                    if li.find("img", class_="bc-crowdstream-item__avatar__image") is not None:
                        i["image"] = li.find("img", class_="bc-crowdstream-item__avatar__image")['src']

                    if li.find("p", class_="bc-helper-nomargin") is not None:
                        link = li.find("p", class_="bc-helper-nomargin").find("a")
                        if link:
                            i['link'] = "https://bugcrowd.com{}".format(li.find("p", class_="bc-helper-nomargin").find("a")['href'])
                            i['title'] = li.find("p", class_="bc-helper-nomargin").find("a").text.replace('\n', "")
                        else:
                            i["title"] = li.find("p", class_="bc-helper-nomargin").text.replace('\n', "")

                    subul = li.find("ul", class_="bc-list")
                    for subli in subul.findAll("li"):
                        if "By" in subli.text:
                            if subli.find("a"):
                                i["foundby"] = subli.find("a").text
                        if "Program" in subli.text:
                            if subli.find("a"):
                                i["vendor"] = subli.find("a").text

                    issues.append(i)

    return issues

def send_to_slack(issues):
    # create slack blocks
    client = slack.WebClient(token=TOKEN)
    block_message = []
    block_message.append(
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "emoji": True,
                "text": "Latest BugCrowd bugs"
            }
        }
    )
    block_message.append(
        {
            "type": "divider"
        }
    )

    for i in issues:
        if i["link"] is not None:
            text = "*<{link}|{title}>*\nReported by {foundby} to {vendor}  |  {bounty}  |  {risk}".format(link=i["link"],
                                                                                                      title=i["title"],
                                                                                                      foundby=i["foundby"],
                                                                                                      vendor=i["vendor"],
                                                                                                      bounty=i["bounty"],
                                                                                                      risk=i["severity"])
        else:
            text = "*{title}*\nReported by {foundby} to {vendor}  |  {bounty}  |  {risk}".format(title=i["title"],
                                                                                                 foundby=i["foundby"],
                                                                                                 vendor=i["vendor"],
                                                                                                 bounty=i["bounty"],
                                                                                                 risk=i["severity"])

        block_message.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                },
                "accessory": {
                    "type": "image",
                    "image_url": "{}".format(i["image"]),
                    "alt_text": "NO IMAGE HERE"
                }
            }
        )

    block_message.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*<https://bugcrowd.com/crowdstream|Go to crowdstream feed>*"
            }
        }
    )

    # post to slack
    response = client.chat_postMessage(channel=CHANNEL, blocks=block_message)
    assert response["ok"]


if __name__ == "__main__":
    issues = get_bc_items(1)
    print("[+] Parsed issues from https://bugcrowd.com/crowdstream")
    send_to_slack(issues)
    print("[+] Sent to slack!")
