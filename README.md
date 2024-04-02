* "News Time Machine" Project, Milestone 1
* Submitted 3/24/2024

* Milestone 2
* Submitted 4/1/2024


# Running the code
1. Build the containers with `docker-compose build`
2. Bring up the docker containers using `docker-compose up`
3. In another terminal, run `./run manage makemigrations` and `./run manage makemigrations news`
4. Run `./run manage migrate`
5. Visit the site at `localhost:8000`

# Accessing the admin view
1. With the docker container running, use `./run manage createsuperuser` to create an admin account
2. Visit `localhost:8000/admin/` to see the admin view