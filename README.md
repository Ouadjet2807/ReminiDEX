# ReminiDex
#### Video Demo: <https://youtu.be/aRlWRvqClJY>
#### Description:

ReminiDex is a flashcard web application built with Flask, SQLite, JavaScript, and Bootstrap.
The flashcard system is based on the principle of active recall — given a term or question, you must retrieve the correct answer from memory.
Actively recalling information helps strengthen neural connections and improves long-term retention more effectively than passive review.

I built this application because I’ve used the flashcard method for years and found it extremely effective for studying.
As I love learning new things, I thought creating my own flashcard app would be the perfect final project for CS50.

## How it works: 

### Account creation:

Start by creating an account. Once logged in, you’ll access your personal dashboard where your lists and folders are displayed.

### Create a list:

Click the “Create” dropdown menu in the navigation bar and select “List”.
You can give your list a title and a short description, then add cards — each with a term (or question) and a definition (or answer).
You can add as many cards as you like (minimum two per list) and delete them individually if needed.

### Organizing with folders:

To store your lists, create folders using the same “Create” dropdown menu.
Once a folder is created, you can:

    - Add lists to it via the “Add content” button,

    - Assign keywords to lists by clicking the ellipsis (⋯) next to them.
      Keywords are unique to each folder and can be created directly from that menu.

### Studying your lists:

In the list view:

    - Click on a card to flip it and see the other side.

    - Navigate with the “Next” and “Previous” buttons.

    - Use Shuffle to randomize the deck.

    - Enable Progress Tracking Mode to switch buttons to “Correct” and “Incorrect.”

Once you’ve gone through the deck, the app displays your score, showing how many cards you got right and wrong.
If you answer certain cards correctly for several days in a row, they’ll be temporarily filtered out from your next sessions.
After some time, they’ll be reintroduced to ensure long-term retention.


### Editing your lists:

You can:

    - Click “Edit this list” from the ellipsis menu,

    - Or click “Add new terms” at the bottom of a list view.

Both actions open the Create List page with the form pre-filled for editing.
You can also edit individual terms directly in the list view by clicking the pencil icon.

### Account management:

In the Account page, you can:

    - Change your password,

    - Delete your account if you wish.


## Tech stack:

    - Backend: Flask (Python)

    - Database: SQLite

    - Frontend: JavaScript, HTML, Sass, Bootstrap

    - Other: Jinja2 templating