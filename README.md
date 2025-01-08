# **GoogleScholar Alert LLM Automatic Summarize**

This is a Python-based program that uses a local LLM to automatically summarize Google Scholar Alert emails. It fetches paper details from emails, processes them with the LLM for summarization, and sends the summaries to a specified recipient email.

## **Features**

- Automatically fetches Google Scholar Alert emails.
- Summarizes paper details using a local LLM.
- Sends the summaries to designated email addresses.

## **Installation**

1. Clone the repository:
   ```bash
   git clone https://github.com/Manticore425/GoogleScholar-Alert-LLM-Automatic-Summarize.git
   cd GoogleScholar-Alert-LLM-Automatic-Summarize
2. Install dependencies:
	```bash
	pip install -r requirements.txt
   ```
	Note: You might need to manually install PyTorch and Llama-CPP-Python, depending on your system configuration.
	

## **Usage**
1. **Configure Email Settings:**
- Enable IMAP/SMTP in your email settings.
- Set up an app-specific password for email access.
- Edit the config/mail.yaml file to configure the email accounts:
	- mail_account: The email receiving Google Scholar Alerts.
	- mail_user: The intermediary email account (if not needed, set it to the recipient email).
	- receivers: The email(s) to receive the LLM-generated summaries.
2. **Set LLM Path:**
In ```main.py```, specify the path to your GGUF-format LLM model.
3. **Run the Program:**
- For a one-time use:
```bash
python main.py
```
- To run daily in the background:
```bash
python process.py
```
You can configure the execution time in process.py.

## **Credits**
Special thanks to [aohenuo (aohenuo's github account)](https://github.com/aohenuo) for contributions and support.

