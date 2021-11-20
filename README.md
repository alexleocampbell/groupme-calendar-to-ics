# GroupMe Calendar to ICS

Turn your GroupMe event calendar into an ICS feed (for Google Calendar, Apple Calendar, Outlook, etc.). Key updates:

 * **Multiple GroupMe group support** - Want to pull events from multiple GroupMe groups? This is now supported!
 * **Pagination support for events** - GroupMe API responds with multiple pages if there are enough events. This is now supported!
 * **Runs on Python 2.7.18** - Configured to run on Heroku-18 (https://devcenter.heroku.com/articles/python-support)

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy?template=https://github.com/alexleocampbell/groupme-calendar-to-ics)

## Deploying

When you set up this app, you'll be required to configure five environment variables:

 * `GROUPME_GROUP_ID` - The ID for the GroupMe group(s). If more than one, list must be comma separated with no spaces e.g. xxxxxx,yyyyyy. Handy tool for finding your Group ID: https://www.schmessage.com/IDFinder/
 * `GROUPME_API_KEY` - A [GroupMe Developer Access Token](https://dev.groupme.com/docs/v3) for a user in the GroupMe group.
 * `CACHE_DURATION` - The duration for which the GroupMe calendar is cached. `0` will disable caching.
 * `GROUPME_CALENDAR_TIMEZONE` - Timezone of the calendar events. See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for list. Default is `America/Los_Angeles`
 * `GROUPME_STATIC_NAME` - The displayed static name for the group calendar (not dynamic due to multiple group support).
 * `GROUPME_PROXY_URL` - *(Optional)* A proxy URL to provide for the calendar.ics.


### Default Settings

 * **Cache Rate** - By default, the GroupMe calendar is refreshed and cached by one request every 60 minutes. This is designed to help rate limit GroupMe API requests. The caching rate can be modified or disabled by setting it to `0`.
