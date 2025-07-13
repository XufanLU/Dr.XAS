## Backend get started 

Enter the repository

```
cd Dr.XAFS 

```
### 1. Create a venv and activate 
```
python -m venv .xas

source .xas/bin/activate
```


### 2. Install the dependencies
```
pip install -r requirements.txt
```

### 3. Set the environment variables

Create a .env file and set your OPENAI_API_KEY

###

### 4. Run Agent backend
```
uvicorn api:app --reload
```

## Frontend get started
Enter the folder
```
cd frontend
```
###  1. Install the dependencies

```
npm i
```


###  2. Start the development server

```
npm run dev
```
you can access the webapp from http://localhost:3000
