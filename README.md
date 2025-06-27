# VSCode Python Virtual Environment and Streamlit Demo

This guide will walk you through setting up a Python virtual environment in Visual Studio Code (VSCode), installing required packages, and running a simple Streamlit application. This is intended for users who may be new to Python, VSCode, or using a terminal.

## 1. Download and Install Visual Studio Code

If you don't already have it, download and install VSCode from the official website:

*   [Download Visual Studio Code](https://code.visualstudio.com/download)

Follow the installation instructions for your operating system (Windows, macOS, or Linux).

## 2. Clone the GitHub Repository

Once you have VSCode installed, the next step is to clone the repository to your local machine.

1.  Open VSCode.
2.  Open the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P`).
3.  Type `Git: Clone` and press Enter.
4.  Paste the following URL and press Enter:
    ```
    https://github.com/DrDavidL/vscode-venv-setup
    ```
5.  Choose a location on your computer to save the project.
6.  Once it's cloned, VSCode will ask if you want to open the repository. Click **Open**.

Now you have all the project files on your computer.

## 3. (Optional) Create a GitHub Account and Install GitHub Extension

If you plan to create your own repositories and share your code on GitHub, you'll need a GitHub account.

1.  **Create a GitHub Account:** Go to [https://github.com/join](https://github.com/join) and sign up for a free account.
2.  **Install the GitHub Extension:** To integrate VSCode with GitHub, install the official **GitHub Pull Requests and Issues** extension.
    *   Open the **Extensions** view in VSCode.
    *   Search for `GitHub Pull Requests and Issues`.
    *   Click **Install**.

This will allow you to manage your repositories, commit code, and handle pull requests directly from within VSCode.

## 4. Install the Python Extension for VSCode

For the best Python experience in VSCode, you'll need the official Python extension from Microsoft.

1.  Open VSCode.
2.  Click on the **Extensions** icon in the Activity Bar on the side of the window (it looks like four squares).
3.  In the search bar, type `Python`.
4.  Find the extension provided by **Microsoft** and click **Install**.


## 5. Setting Up the Python Virtual Environment

A virtual environment is a self-contained directory that holds a specific version of Python, plus a number of additional packages. Using a virtual environment is a best practice to avoid conflicts between projects that may require different versions of the same package.

### Step 1: Open the Project Folder in VSCode

*   If you have this project on your computer, open VSCode and go to `File > Open Folder...` and select the folder containing this `README.md` file.

### Step 2: Create the Virtual Environment

1.  Open the **Command Palette** in VSCode. You can do this in two ways:
    *   Go to `View > Command Palette...` from the top menu.
    *   Use the keyboard shortcut: `Ctrl+Shift+P` (on Windows/Linux) or `Cmd+Shift+P` (on macOS).

2.  In the Command Palette, type `Python: Create Environment` and select it from the list.


3.  You will be prompted to select a virtual environment type. Choose **Venv**.

4.  Next, you'll be asked to select a Python interpreter. Choose a recommended version of Python (usually Python 3.8 or higher). If you don't have Python installed, VSCode may prompt you to install it.

5.  VSCode will now create a new folder in your project named `.venv`. This folder contains your virtual environment.

### Step 3: Activate the Virtual Environment

VSCode should automatically select and activate the new environment for you. You can verify this by looking at the bottom-right corner of the VSCode window. It should show the Python version from your virtual environment (e.g., `Python 3.x.x ('.venv')`).


If it's not selected, you can click on the Python version in the status bar and choose the one that has `('.venv')` next to it.

**How to be sure you are using the virtual environment:**

When you open a new terminal in VSCode (`Terminal > New Terminal`), you should see `(.venv)` at the beginning of your terminal prompt. This indicates that the virtual environment is active.

*   **On macOS/Linux:** `(.venv) your-username@your-computer:~$`
*   **On Windows:** `(.venv) C:\path\to\your\project>`

If you don't see this, it means the environment is not active in that terminal. You can manually activate it by running the correct script:
*   **On macOS/Linux:** `source .venv/bin/activate`
*   **On Windows (Command Prompt):** `.venv\Scripts\activate.bat`
*   **On Windows (PowerShell):** `.venv\Scripts\Activate.ps1`

## 6. Install Project Requirements

This project uses a `requirements.txt` file to list all the Python packages it needs to run.

1.  Make sure your virtual environment is active (check for `(.venv)` in your terminal prompt).
2.  In the VSCode terminal, run the following command to install the necessary packages:

    ```bash
    pip install -r requirements.txt
    ```

    `pip` is the package installer for Python. This command tells `pip` to read the `requirements.txt` file and install all the packages listed inside it.

## 7. Run the Streamlit App

Once the requirements are installed, you can run the Streamlit demo app.

1.  In the same terminal, run this command:

    ```bash
    streamlit run app.py
    ```

2.  This will start a local web server and open a new tab in your web browser with the running application.

## The Importance of the `.gitignore` File

You will notice a file in this project called `.gitignore`. This is a very important file for projects that use Git for version control (like on GitHub).

**What does it do?**

The `.gitignore` file tells Git which files and folders it should **ignore** and not track. When you commit your code, any files or patterns listed in `.gitignore` will not be included.

**Why is this important?**

1.  **To Exclude Sensitive Information:** You should never commit files containing sensitive data like API keys, passwords, or other credentials. These can be listed in `.gitignore`.
2.  **To Keep the Repository Clean:** Your project will generate many files that are specific to your local machine or are temporary. The virtual environment folder (`.venv`), compiled Python files (`__pycache__`), and system-specific files (`.DS_Store` on macOS) do not need to be shared with others.
3.  **To Reduce Repository Size:** By ignoring large, generated files, you keep the size of your repository small, making it faster to clone and work with.

In this project, the `.gitignore` file is configured to ignore the `.venv` folder, among other common Python and system files. This is why you don't see the `.venv` folder when you view the project on GitHub, even though it exists on your local machine.
