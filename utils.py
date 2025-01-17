from icalendar import Calendar, Event
from flask import Response
from collections import defaultdict
import dateutil.parser
import requests
import urlparse
import urllib
from flask import current_app


def return_ics_Response(response_body):
    return Response(
        response_body,
        mimetype='text/calendar',
        headers={'Content-Disposition': 'attachment'}
    )


def build_ics_urls(ics_url):
    google_calendar_url_base = 'http://www.google.com/calendar/render?cid='

    # Parse the URL into [scheme, netloc, path, params, query, fragment]
    parsed_ics_url = list(urlparse.urlparse(ics_url))
    if parsed_ics_url[0] != 'https':
        parsed_ics_url[0] = 'http'
    ics_url_http = urlparse.urlunparse(parsed_ics_url)

    parsed_ics_url[0] = 'webcal'
    ics_url_webcal = urlparse.urlunparse(parsed_ics_url)

    parsed_google_url = list(urlparse.urlparse(google_calendar_url_base))
    parsed_google_url[4] = dict(urlparse.parse_qsl(parsed_google_url[4]))
    parsed_google_url[4]['cid'] = ics_url_webcal
    parsed_google_url[4] = urllib.urlencode(parsed_google_url[4])
    ics_url_google = urlparse.urlunparse(parsed_google_url)

    return ics_url_http, ics_url_webcal, ics_url_google


def load_groupme_json(app, groupme_api_key, groupme_group_id):
    
    groupme_group_id_list = groupme_group_id.split(',')
    current_app.groupme_calendar_json_cache = []
    current_app.groupme_calendar_details = defaultdict(list)

    # Create a blank list for failing GroupID requests
    current_app.failed_groups = ""

    for groupme_group in groupme_group_id_list:
        # Fetch data from GroupMe APIs
        url_group_info = 'https://api.groupme.com/v3/groups/{groupme_group}'.format(groupme_group=groupme_group)
        url_calendar = 'https://api.groupme.com/v3/conversations/{groupme_group}/events/list'.format(groupme_group=groupme_group)
        headers = {'X-Access-Token': groupme_api_key}

        response = requests.get(url_calendar, headers=headers)
        if response.status_code != 200:
            current_app.groupme_load_successfully = False
            app.logger.error('GroupID {}: Status Code {}: {}'.format(groupme_group, response.status_code, response.text))
            current_app.failed_groups += "{} ".format(groupme_group)
            continue
            # This goes back to beginning of for loop as we no longer "return False" for failed GroupID requests

        current_app.groupme_calendar_json_cache.append(response.json())

        # Reset pagination values
        has_next_key = False
        nextkey = ""

        # Check if response has pagination 
        if response.json().get('response', {}).get('next', None):
            has_next_key = True
            nextkey = response.json().get('response', {}).get('next')
        
        # Append paginated pages while they exist
        while has_next_key:
            url_calendar_next = 'https://api.groupme.com{nextkey}'.format(nextkey=nextkey)
            response = requests.get(url_calendar_next, headers=headers)

            if response.status_code != 200:
                current_app.groupme_load_successfully = False
                app.logger.error('{}: {}'.format(response.status_code, response.text))
                return False

            current_app.groupme_calendar_json_cache.append(response.json())

            if response.json().get('response', {}).get('next', None):
                nextkey = response.json().get('response', {}).get('next')
            else:
                has_next_key = False
                # no next_key, stop the loop

        # Get group name and group share URL
        response = requests.get(url_group_info, headers=headers)
        if response.status_code == 200:
            # Append name of the group 
            if response.json().get('response', {}).get('name', None):
                current_app.groupme_calendar_details.setdefault(groupme_group, []).append(response.json().get('response', {}).get('name'))
                # Set name of calendar to last fetched group. Currently using static defined name instead of this.
                # current_app.groupme_calendar_name = response.json().get('response', {}).get('name')

            # Append share URL for the group
            if response.json().get('response', {}).get('share_url', None):
                current_app.groupme_calendar_details.setdefault(groupme_group, []).append(response.json().get('response', {}).get('share_url'))

    # If there were any failed GroupID requests, log them in one simple string
    if current_app.failed_groups:
        app.logger.error('GroupID Error(s): {}'.format(current_app.failed_groups))

    current_app.groupme_load_successfully = True
    return True


def groupme_json_to_ics(groupme_json, static_name=None):
    cal = Calendar()
    cal['prodid'] = '-//Alexander Campbell//GroupMe-to-ICS 2.0//EN'
    cal['version'] = '2.0'
    cal['calscale'] = 'GREGORIAN'
    cal['method'] = 'PUBLISH'
    cal['x-wr-calname'] = '{} GroupMe'.format(current_app.groupme_calendar_name)
    cal['x-wr-timezone'] = current_app.calendar_timezone

    for groupme_json_item in groupme_json:
        for json_blob in groupme_json_item['response']['events']:
            if 'deleted_at' not in json_blob:
                event = Event()
                event['uid'] = json_blob['event_id']
                event.add('dtstart', dateutil.parser.parse(json_blob['start_at']))
                if json_blob.get('end_at'):
                    event.add('dtend', dateutil.parser.parse(json_blob['end_at']))
                event['summary'] = json_blob['name']
                event['description'] = json_blob.get('description', '')
                if json_blob.get('location'):
                    location = json_blob.get('location', {})

                    if json_blob.get('description'):
                        event['description'] += '\n\n'
                    event['description'] += 'Location:\n'

                    if location.get('name') and location.get('address'):
                        event['location'] = "{}, {}".format(location.get('name').encode('utf-8'), location.get('address').strip().replace("\n", ", ").encode('utf-8'))
                        event['description'] += location.get('name')
                        event['description'] += '\n'
                        event['description'] += location.get('address')
                    elif location.get('name'):
                        event['location'] = location.get('name')
                        event['description'] += location.get('name')
                    elif location.get('address'):
                        event['location'] = location.get('address').strip().replace("\n", ", ")
                        event['description'] += location.get('address')

                    if location.get('lat') and location.get('lng'):
                        location_url = 'https://www.google.com/maps?q={},{}'.format(location.get('lat'), location.get('lng'))
                        if not event.get('location'):
                            event['location'] = location_url
                        else:
                            event['description'] += '\n'
                        event['description'] += location_url

                # Get the details for this particular GroupMe group 
                details = current_app.groupme_calendar_details[json_blob['conversation_id']]

                # Add spacing if there was a description
                if event['description']:
                    event['description'] += '\n\n'
                
                # Adds GroupMe name and link to each calendar entry 
                event['description'] += 'Posted in: '
                event['description'] += '<a href="{}" target="_blank">'.format(details[1])
                event['description'] += details[0]
                event['description'] += ' chat</a>'

                if json_blob.get('updated_at'):
                    event['last-modified'] = dateutil.parser.parse(json_blob.get('updated_at'))
                cal.add_component(event)

    return cal.to_ical()


def groupme_ics_error(error_text, static_name=None):
    cal = Calendar()
    cal['prodid'] = '-//Alexander Campbell//GroupMe-to-ICS 2.0//EN'
    cal['version'] = '2.0'
    cal['calscale'] = 'GREGORIAN'
    cal['method'] = 'PUBLISH'
    cal['x-wr-calname'] = 'GroupMe: {} ({})'.format(current_app.groupme_calendar_name, error_text)
    cal['x-wr-timezone'] = 'America/Los_Angeles'

    return cal.to_ical()