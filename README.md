# api_for_articles
For testing this API I would recommend using "/docs" path on the API URL (http://localhost:8000).
In the Dockerimage the API is hosted on port 8000.
For the simple database I decided to use json files.
The app operates on two jsons: "users.json" and "articles.json". The id keys in these files are "username" and "title" since I assumed that there would be no users of the same username and no duplicate article titles.
To handle authentication and authorization I implemented JSON Web Tokens. Users are restricted from adding articles if they are not authenticated. They are restricted from updating/removing objects that are not their properties.
