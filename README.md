# Setting up
In order for this to work, you must have a cvs file that contains all the title ids.
Once you place the Games.cvs file next to archive.py, run it until its done.
archive.py will cache and save the data pulled from the marketplace.
finally, run the run.py to start the webserver and your done.

# Templates
for the Home page check /templates/home.html, for game template its template.html

# notes
there is an api endpoint to allow sharing cached data easier so people are not
spamming the marketplace servers. (<host_name>/api/xml/<title_id>)

I am not a security expert, but the data should be sanatized(which its not)
so use at your own risk.
