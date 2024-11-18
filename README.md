# Calendar App

This is a simple calendar app that allows users to manage events within a specified date range. The application is containerized using Docker for easy setup and deployment.

## Prerequisites

Before you begin, ensure you have the following tools installed:

- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

## 1. Clone the Repository

To get started, clone the repository to your local machine:

```bash
git clone https://github.com/SergeyDev1996/Calendar.git
cd calendar-app
```

## 2. Set Environment Variables
The app requires the start and end dates for the date range to be set via environment variables. Create a .env file in the root of the project and add the following entries:
##### CREDENTIALS_FILE_PATH=
##### SPREADSHEET_URL=
##### START_DATE=
##### END_DATE=
CREDENTIALS_FILE_PATH is the file with credentials of the google developer account.

## 3. Build and Run the Docker Container
```
docker-compose up --build
```
After the up is running, please fully copy the link in the browser, and follow the instructions from google. The gathered information will be automatically
pushed to the spreadsheet. 