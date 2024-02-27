# Shortcut key
1. ctrl + c (in terminal) --> quit terminal
2. ctrl + p --> command palette , (enter '>' in command palette to find the command, or ctrl + shift + p instead)
3. ctrl + shift + v (in README) --> preview README :>
4. ctrl + shift + d , f5 --> debug and run
5. f10 (during debug) --> next step
6. 

# Admin side account
Email : kexintankx@gmail.com
Password : Admin

# To create super user
1. `py manage.py createsuperuser` 

# Create super admin
1. py manage.py createsuperuserandstaff   

# Run the code
py manage.py runserver

# To make migrations
1. `py manage.py makemigrations` --> check the update models and compare with current database 
2. `py manage.py migrate` --> translate to sql script

# Login tester account
1. Investigator
STF00003@proofinder.com
Yhw20020310

STF00005@proofinder.com
Klw20010915

STF00008@proofinder.com
Jo20000918

2. Chemist
STF00004@proofinder.com
Klq20000927

STF00006@proofinder.com
Yl20011015

3. Pathologist
STF00005@proofinder.com
Jy20011018

STF00007@proofinder.com
Slyt20011224

# How to drop the database
1. Go to workbench
2. right click fyp-sql in left hand side bar
3. select drop-schema
4. select drop-now
5. choose the create new schema (4th icon on top)
5. enter 'fyp-sql' in name input
6. select apply
7. go the visual studio code
8. open the migrations folder > _pycache in left hand side bar, and delete the 0001....pyc/.py file (init don't DELETE)
9. make migration then migrate 
10. complete!


# Notes
(JS)
1. AddEventListener = Event means the action element will do ( example: input, hover, focus, click)
2. var = a global or local scope which can declared outside and inside function
