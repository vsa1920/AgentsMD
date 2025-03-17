# AI Triage System Demo

This is a web-based demonstration of the AI Triage System, which uses a multi-agent approach to determine Emergency Severity Index (ESI) levels for patients based on nurse-patient conversations.

## Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key in a `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
   Alternatively, you can enter your API key in the web interface.

3. Run the demo:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to `http://127.0.0.1:5000/`

## Using the Demo

1. Enter a patient-nurse conversation in the text area
2. Select the LLM model to use (GPT-4o Mini is recommended for speed)
3. Click "Process Case"
4. View the quick reference output
5. Use the buttons to view detailed output or the full agent discussion
6. Download any of the outputs using the download buttons

## Output Files

The demo creates three types of output files in separate directories:

- `demo/quick_ref/`: Quick reference files for nurses
- `demo/results/`: Detailed assessment results
- `demo/discussions/`: Full agent discussions

## Example Case

Here's a simple example case you can use to test the system: 