# **README_SOFTWARE.md** – AI Coffee Machine Project

## **Table of Contents**

- [Web App Module Documentation](#web-app-module-documentation)
- [Machine Learning Module Documentation](#machine-learning-module-documentation)

---

## **Web App Module Documentation**

### **Overview**

The **Web App** module serves as the frontend for the **AI Coffee Machine** project, providing users with a seamless interface to interact with the coffee machine. It enables users to submit their coffee preferences, view brewing history, and receive real-time feedback. Built using **React** and **Vite**, the frontend communicates with the backend through API calls, displaying the brewing results and allowing for smooth user interaction.

---

### **Pages in the Web App**

1. **Welcome.jsx**  
   The **Welcome** component is the first screen users see when they open the web app. It introduces the AI Coffee Machine, giving a brief overview of the system and providing a button for users to get started. The user can navigate to the login page from here.

2. **Register.jsx**  
   The **Register** page allows new users to create an account by providing an email and password. It includes form validation and error handling for failed registration attempts. After successful registration, users are redirected to the home page.

3. **Login.jsx**  
   The **Login** component enables existing users to sign in using their email and password, or they can sign in with Google. If authentication is successful, users are directed to the home page. If there are errors during login, they are displayed for the user.

4. **Home.jsx**  
   The **Home** page is the central hub where users interact with the AI Coffee Machine. They can enter coffee preferences, adjust serving sizes, and send brew requests to the backend. It also displays a list of recent brews and allows users to leave feedback on their past brews.

5. **Machine.jsx**  
   The **Machine** page provides users with a detailed view of the brewing process, including machine commands and real-time progress tracking. It enables users to view the status of their brew, including the current stage of the brewing process.

6. **CoffeeDetails.jsx**  
   This page shows detailed information about a specific coffee, including flavor notes, brewing instructions, and characteristics like bitterness, acidity, and sweetness. Users can view a coffee's details and initiate a brew directly from this page.

7. **Account.jsx**  
   The **Account** page allows users to view their profile information, such as name, email, and account creation date. It also provides an option for users to delete their accounts or manage saved brews (though this feature is not fully implemented).

---

### **Components in the Web App**

1. **NavBar.jsx**  
   The **NavBar** component is responsible for rendering the navigation bar that appears at the top of the app. It provides links to the main sections of the app, such as Home, Machine, and Account. It also includes a logout button that allows users to sign out.

2. **MachineCodeVisualization.tsx**  
   The **MachineCodeVisualization** component visualizes the brewing process, displaying steps like grinding, dispensing, brewing, and extraction. It tracks and shows real-time updates as the brew progresses, allowing users to follow the process visually.

3. **FeedbackModal.jsx**  
   The **FeedbackModal** component allows users to leave feedback on their brewed coffee. It provides a rating system and an optional text area for additional notes, helping improve future brewing recommendations.

4. **CoffeeCard.jsx**  
   The **CoffeeCard** component displays a preview of a coffee with its name, description, and image. It is used in sections like featured coffees, where users can click on a coffee to view more details.

5. **BrewHistoryCard.jsx**  
   The **BrewHistoryCard** component shows a saved brewing session with details like the coffee flavor, parameters, and the time it was brewed. It includes options to "Brew Again," save the brew, or delete it from saved brews.

6. **BeanScanner.jsx**  
   The **BeanScanner** component uses the camera to scan coffee bags and detect the bean type, roast, and other characteristics. It captures the front and back images of the coffee bag and processes them for further identification.

---

### **How the Web App Works**

#### **1. User Interaction**
- The user interacts with the **Home** page to submit their coffee preferences and select a serving size.
- They can also browse coffee details via **CoffeeDetails.jsx** and view saved brews in **Account.jsx**.

#### **2. Backend Communication**
- The web app communicates with the backend via **FastAPI** to send the brew request and fetch brewing history.

#### **3. Display Feedback**
- Once the brew is processed, the system shows personalized recommendations, and users can provide feedback via **FeedbackModal.jsx**.

---

### **Dev/Build Tool Information**

- **Node.js 14.x**: Required for the development environment.
- **Vite 2.x**: Used for bundling and building the app.
- **React 17.x**: JavaScript library used to build the user interface.
- **ESLint 7.x**: For linting and maintaining code quality.

---

### **How to Install the Web App Software Stack**

1. **Install Dependencies**:
   - Ensure that you have **Node.js 14.x** installed.
   - Install project dependencies:
     ```bash
     npm install
     ```

2. **Start the Web App**:
   - Run the development server:
     ```bash
     npm run dev
     ```

3. **Build for Production**:
   - To build the project for production:
     ```bash
     npm run build
     ```

---

![Frontend Flowchart](images/web_flowchart.png)

---

## **Machine Learning Module Documentation**

### **Overview**

The **Machine Learning (ML)** module is a core component of the **AI Coffee Machine** project, responsible for processing user input, personalizing coffee brewing recommendations, and executing the brewing process. It integrates several components that work together to provide accurate, real-time suggestions based on user preferences, past interactions, and user feedback. The ML model continuously learns and adapts based on feedback, improving over time.

This section documents the **ML pipeline** and its key components, including how they work in **`main.py`**, which serves as the central execution point for the ML system.

---

### **Software Modules in the ML Pipeline**

The ML pipeline in the AI Coffee Machine project is implemented in **`main.py`**, and interacts with various other components for data processing, user interaction, feedback handling, and brewing execution.

1. **main.py**  
   This is the main entry point for the system, containing the FastAPI server and the logic that executes all processes, from receiving user input to making brewing recommendations and executing machine commands.

2. **Brew Request Handling**  
   This component processes incoming brew requests, handles user interactions, and retrieves past brewing data and feedback from Firestore. It plays a critical role in collecting data for personalized brewing recommendations.

3. **Feedback Loop**  
   The feedback loop collects user feedback after every brewing cycle. It stores feedback in **Firestore** and processes it to refine future brewing recommendations.

4. **Prompt Generation**  
   This module generates a structured prompt to feed to the **GPT-4 API** based on the user's input and brewing data. The prompt is tailored to capture the nuances of the user’s coffee preferences.

5. **LLM Handler**  
   The **LLMHandler** interfaces with the **GPT-4 API**, sending the generated prompts and receiving responses, which include personalized brewing recommendations. These responses are parsed and processed to extract actionable brewing instructions.

6. **ML Personalization**  
   After receiving the LLM output, the **ML Personalization** module customizes the brewing parameters (e.g., grind size, extraction time, temperature) to suit the individual user's preferences.

7. **Brew Execution**  
   This component generates machine commands based on personalized parameters and sends them to the **Coffee Machine API**, which controls the brewing process, including grinding, heating, and pumping.

8. **Storage & Logging**  
   All brewing and feedback data is stored in **Firestore**, ensuring that feedback, historical brews, and system logs are tracked and available for future interactions.

---

### **Machine Learning Pipeline Flow**

Below is a flowchart of the **ML pipeline** as described by the diagram you provided, illustrating the dependencies between the key modules:

![ML Pipeline Flowchart](images/ml_flowchart.png)

The flowchart shows the sequential steps of the ML process, starting from user interaction through to feedback processing and final execution. 

---

### **How the ML System Works**

#### **1. User Interaction**
- The user submits their coffee preference as a **natural language request** (e.g., "I want a fruity espresso with chocolate notes").
- This input is sent to **FastAPI** as part of the `/brew` route.

#### **2. Brew Request Handling**
- **FastAPI** handles the incoming brew request.
- It retrieves historical brewing data and feedback from **Firestore** to personalize the recommendations based on previous interactions.

#### **3. Feedback Loop**
- **User Feedback**: After each brewing cycle, users provide feedback on the coffee (e.g., rating it from 1-5 or providing comments).
- The feedback is saved in **Firestore** and summarized for **ML tuning**, helping improve future recommendations.

#### **4. Prompt Generation**
- The system builds a structured prompt that combines user preferences and historical data. This prompt is prepared by the **PromptGenerator** and sent to the **GPT-4 API** for interpretation.

#### **5. LLM Interpretation (GPT-4 API)**
- **GPT-4** processes the prompt and generates a response in the form of a **brewing JSON**, containing all the recommended brewing parameters (e.g., grind size, extraction time, temperature).
- The response is parsed and sanitized to ensure it is usable by the system.

#### **6. ML Personalization**
- The system personalizes the brewing parameters based on the user's input and feedback. This step adjusts key variables like grind size, extraction time, and water temperature to match the user’s preferences.

#### **7. Brew Execution**
- The final **personalized parameters** are used to generate machine commands (e.g., grind settings, heat levels, pump time).
- These commands are sent to the **Coffee Machine API** to execute the brewing process.

#### **8. Storage & Logging**
- **Brew data** and **user feedback** are stored in **Firestore**, enabling continuous refinement and logging of brewing results for future reference.

---

### **Dev/Build Tool Information**

The following tools and libraries are required for the development and execution of the ML module:

- **Python 3.8.1**: Python was used for the development of all ML code. Ensure to use Python 3.8.x or later.
- **FastAPI 0.63**: For building the web server that handles incoming brew requests and integrates the ML model.
- **TensorFlow 2.4**: Used for initial ML model training and evaluation (regression models like Random Forest, Gradient Boosting, and Linear Regression).
- **OpenAI GPT-4 API**: Used for generating personalized recommendations based on user input.
- **scikit-learn 0.24.2**: For building and evaluating traditional ML models (Random Forest, Gradient Boosting).
- **pandas 1.2.4**: For data manipulation and preprocessing.
- **requests 2.25.1**: For making HTTP requests to external services like GPT-4 and the Coffee Machine API.

---

### **How to Install the Machine Learning Software Stack from Scratch**

1. **Prepare Your Environment**:  
   - Ensure that you have **Python 3.8+** installed.
   - Create a new Python virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

2. **Install Dependencies**:
   - Install the necessary Python libraries:
     ```bash
     pip install fastapi==0.63
     pip install tensorflow==2.4
     pip install scikit-learn==0.24.2
     pip install pandas==1.2.4
     pip install openai==0.11.3
     pip install requests==2.25.1
     pip install firebase-admin==4.5.0
     pip install python-dotenv==0.17.1
     ```

3. **Set Up GPT-4 API Access**:
   - Sign up for **OpenAI GPT-4 API** access and obtain your API key from [OpenAI](https://www.openai.com/).
   - Set up environment variables in the backend folder for secure access to the API:
     ```bash
     export OPENAI_API_KEY="your-api-key-here"
     ```

4. **Clone Repository**:
   - Clone the repository and navigate to the project folder:
     ```bash
     git clone https://github.com/NaomiGonz/AICoffee-Machine.git
     cd backend
     ```

5. **Run the ML Model**:
   - Start the ML system with the following command, which will also start the FastAPI server:
     ```bash
     python main.py
     ```
