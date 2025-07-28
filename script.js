// js/script.js
// This file contains all the JavaScript logic for your web frontend.
// It handles user interactions, dynamically generates forms, builds CLI commands,
// and manages the display of generated commands and log content.

// 1. Get references to HTML elements:
// We use document.getElementById() to get a reference to specific elements in our HTML
// by their unique 'id' attribute. This allows JavaScript to interact with them (read their value,
// change their content, add event listeners, etc.).
const orderTypeSelect = document.getElementById('orderType'); // The dropdown for selecting order type
const orderFormsDiv = document.getElementById('orderForms');   // The div where dynamic forms will be inserted
const commandOutputDiv = document.getElementById('commandOutput'); // The div showing the generated command
const generatedCommandPre = document.getElementById('generatedCommand'); // The <pre> tag where the command text goes
const copyBtn = document.getElementById('copyBtn');             // The "Copy" button for the command
const copyMessageP = document.getElementById('copyMessage');   // The "Copied to clipboard!" message
const logInputTextarea = document.getElementById('logInput');   // The textarea for pasting bot.log content
const displayLogBtn = document.getElementById('displayLogBtn'); // The "Display Log" button
const logOutputDiv = document.getElementById('logOutput');     // The div where the log content will be displayed

// 2. Function to dynamically show/hide order forms based on selection:
// This function is called when the user changes the selection in the 'orderType' dropdown.
function showOrderForm() {
    // Get the value of the currently selected option in the dropdown.
    const selectedType = orderTypeSelect.value;
    
    // Clear any previously injected form HTML to ensure only one form is visible at a time.
    orderFormsDiv.innerHTML = ''; 
    
    // Hide the command output area and copy message initially. They will be shown when a command is generated.
    commandOutputDiv.classList.add('hidden'); // 'hidden' is a Tailwind CSS class that sets display: none.
    copyMessageP.classList.add('hidden');     // Hides the "Copied to clipboard!" message.

    let formHtml = '';           // String to build the HTML for the input form.
    let generateButtonHtml = ''; // String to build the HTML for the "Generate Command" button.

    // Use a switch statement to handle different order types.
    // Each case defines the specific input fields required for that order type.
    switch (selectedType) {
        case 'check-balance':
            // For 'check-balance', no input fields are needed, just a generate button.
            generateButtonHtml = `<button onclick="generateCommandWrapper('check-balance')" class="btn">Generate Command</button>`;
            break;
        case 'market-order':
            // Input fields for Market Order: Symbol, Side, Quantity.
            // 'input-field' class is for styling. 'required' makes them mandatory.
            // 'step="any"' allows decimal numbers for quantity.
            formHtml = `
                <input type="text" id="symbol" placeholder="Symbol (e.g., BTCUSDT)" class="input-field" required>
                <select id="side" class="input-field" required>
                    <option value="">Select Side</option>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                </select>
                <input type="number" id="quantity" placeholder="Quantity (e.g., 0.001)" step="any" class="input-field" required>
            `;
            generateButtonHtml = `<button onclick="generateCommandWrapper('market-order')" class="btn">Generate Command</button>`;
            break;
        case 'limit-order':
            // Input fields for Limit Order: Symbol, Side, Quantity, Price.
            formHtml = `
                <input type="text" id="symbol" placeholder="Symbol (e.g., BTCUSDT)" class="input-field" required>
                <select id="side" class="input-field" required>
                    <option value="">Select Side</option>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                </select>
                <input type="number" id="quantity" placeholder="Quantity (e.g., 0.001)" step="any" class="input-field" required>
                <input type="number" id="price" placeholder="Price (e.g., 30000.0)" step="any" class="input-field" required>
            `;
            generateButtonHtml = `<button onclick="generateCommandWrapper('limit-order')" class="btn">Generate Command</button>`;
            break;
        case 'oco-order':
            // Input fields for OCO Order: Symbol, Side, Quantity, Stop Price, Take Profit Price.
            formHtml = `
                <input type="text" id="symbol" placeholder="Symbol (e.g., BTCUSDT)" class="input-field" required>
                <select id="side" class="input-field" required>
                    <option value="">Select Side (Closing Position)</option>
                    <option value="BUY">BUY (to close SELL position)</option>
                    <option value="SELL">SELL (to close BUY position)</option>
                </select>
                <input type="number" id="quantity" placeholder="Quantity (e.g., 0.001)" step="any" class="input-field" required>
                <input type="number" id="stop-price" placeholder="Stop Price (e.g., 116000.0)" step="any" class="input-field" required>
                <input type="number" id="take-profit-price" placeholder="Take Profit Price (e.g., 118000.0)" step="any" class="input-field" required>
            `;
            generateButtonHtml = `<button onclick="generateCommandWrapper('oco-order')" class="btn">Generate Command</button>`;
            break;
        case 'stop-limit-order':
            // Input fields for Stop-Limit Order: Symbol, Side, Quantity, Stop Price, Limit Price.
            formHtml = `
                <input type="text" id="symbol" placeholder="Symbol (e.g., BTCUSDT)" class="input-field" required>
                <select id="side" class="input-field" required>
                    <option value="">Select Side</option>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                </select>
                <input type="number" id="quantity" placeholder="Quantity (e.g., 0.001)" step="any" class="input-field" required>
                <input type="number" id="stop-price" placeholder="Stop Price (e.g., 117500.0)" step="any" class="input-field" required>
                <input type="number" id="limit-price" placeholder="Limit Price (e.g., 117510.0)" step="any" class="input-field" required>
            `;
            generateButtonHtml = `<button onclick="generateCommandWrapper('stop-limit-order')" class="btn">Generate Command</button>`;
            break;
        case 'twap-order':
            // Input fields for TWAP Order: Symbol, Side, Total Quantity, Number of Intervals, Interval Seconds.
            formHtml = `
                <input type="text" id="symbol" placeholder="Symbol (e.g., BTCUSDT)" class="input-field" required>
                <select id="side" class="input-field" required>
                    <option value="">Select Side</option>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                </select>
                <input type="number" id="total-quantity" placeholder="Total Quantity (e.g., 0.003)" step="any" class="input-field" required>
                <input type="number" id="num-intervals" placeholder="Number of Intervals (e.g., 3)" step="1" class="input-field" required>
                <input type="number" id="interval-seconds" placeholder="Interval Seconds (e.g., 5)" step="1" class="input-field" required>
            `;
            generateButtonHtml = `<button onclick="generateCommandWrapper('twap-order')" class="btn">Generate Command</button>`;
            break;
        case 'grid-order':
            // Input fields for Grid Order: Symbol, Min Price, Max Price, Num Buy Orders, Num Sell Orders, Quantity Per Order.
            formHtml = `
                <input type="text" id="symbol" placeholder="Symbol (e.g., BTCUSDT)" class="input-field" required>
                <input type="number" id="min-price" placeholder="Min Price (e.g., 110000.0)" step="any" class="input-field" required>
                <input type="number" id="max-price" placeholder="Max Price (e.g., 120000.0)" step="any" class="input-field" required>
                <input type="number" id="num-buy-orders" placeholder="Num Buy Orders (e.g., 3)" step="1" class="input-field" required>
                <input type="number" id="num-sell-orders" placeholder="Num Sell Orders (e.g., 3)" step="1" class="input-field" required>
                <input type="number" id="quantity-per-order" placeholder="Quantity Per Order (e.g., 0.001)" step="any" class="input-field" required>
            `;
            generateButtonHtml = `<button onclick="generateCommandWrapper('grid-order')" class="btn">Generate Command</button>`;
            break;
        default:
            // If no valid option is selected, clear forms and buttons.
            break;
    }

    // Inject the generated HTML into the 'orderFormsDiv'.
    if (formHtml) {
        orderFormsDiv.innerHTML = formHtml + `<div class="mt-4">${generateButtonHtml}</div>`;
    } else if (generateButtonHtml) {
        // For 'check-balance' which only has a button.
        orderFormsDiv.innerHTML = generateButtonHtml;
    }
}

// 3. Wrapper function for generateCommand:
// This function is used by the 'onclick' attributes in the HTML buttons.
// It simply calls the main 'generateCommand' function with the correct command type.
function generateCommandWrapper(commandType) {
    generateCommand(commandType);
}

// 4. Function to generate the CLI command string:
// This function reads values from the dynamically created input fields and constructs the CLI command.
function generateCommand(commandType) {
    // Start with the base command.
    let command = `python bot.py ${commandType}`;
    let isValid = true; // Flag to check if all required fields are filled.

    // Helper function to get the value of an input field by its ID.
    // The '?' (optional chaining) ensures it doesn't throw an error if the element doesn't exist.
    const getInputValue = (id) => document.getElementById(id)?.value;

    // Build the command string based on the command type.
    // For each case, it retrieves input values and appends them as command-line arguments.
    // It also checks if all required inputs have values.
    switch (commandType) {
        case 'market-order':
            const marketSymbol = getInputValue('symbol');
            const marketSide = getInputValue('side');
            const marketQuantity = getInputValue('quantity');
            if (!marketSymbol || !marketSide || !marketQuantity) isValid = false;
            command += ` --symbol ${marketSymbol} --side ${marketSide} --quantity ${marketQuantity}`;
            break;
        case 'limit-order':
            const limitSymbol = getInputValue('symbol');
            const limitSide = getInputValue('side');
            const limitQuantity = getInputValue('quantity');
            const limitPrice = getInputValue('price');
            if (!limitSymbol || !limitSide || !limitQuantity || !limitPrice) isValid = false;
            command += ` --symbol ${limitSymbol} --side ${limitSide} --quantity ${limitQuantity} --price ${limitPrice}`;
            break;
        case 'oco-order':
            const ocoSymbol = getInputValue('symbol');
            const ocoSide = getInputValue('side');
            const ocoQuantity = getInputValue('quantity');
            const stopPrice = getInputValue('stop-price');
            const takeProfitPrice = getInputValue('take-profit-price');
            if (!ocoSymbol || !ocoSide || !ocoQuantity || !stopPrice || !takeProfitPrice) isValid = false;
            command += ` --symbol ${ocoSymbol} --side ${ocoSide} --quantity ${ocoQuantity} --stop-price ${stopPrice} --take-profit-price ${takeProfitPrice}`;
            break;
        case 'stop-limit-order':
            const slSymbol = getInputValue('symbol');
            const slSide = getInputValue('side');
            const slQuantity = getInputValue('quantity');
            const slStopPrice = getInputValue('stop-price');
            const slLimitPrice = getInputValue('limit-price');
            if (!slSymbol || !slSide || !slQuantity || !slStopPrice || !slLimitPrice) isValid = false;
            command += ` --symbol ${slSymbol} --side ${slSide} --quantity ${slQuantity} --stop-price ${slStopPrice} --limit-price ${slLimitPrice}`;
            break;
        case 'twap-order':
            const twapSymbol = getInputValue('symbol');
            const twapSide = getInputValue('side');
            const totalQuantity = getInputValue('total-quantity');
            const numIntervals = getInputValue('num-intervals');
            const intervalSeconds = getInputValue('interval-seconds');
            if (!twapSymbol || !twapSide || !totalQuantity || !numIntervals || !intervalSeconds) isValid = false;
            command += ` --symbol ${twapSymbol} --side ${twapSide} --total-quantity ${totalQuantity} --num-intervals ${numIntervals} --interval-seconds ${intervalSeconds}`;
            break;
        case 'grid-order':
            const gridSymbol = getInputValue('symbol');
            const minPrice = getInputValue('min-price');
            const maxPrice = getInputValue('max-price');
            const numBuyOrders = getInputValue('num-buy-orders');
            const numSellOrders = getInputValue('num-sell-orders');
            const quantityPerOrder = getInputValue('quantity-per-order');
            if (!gridSymbol || !minPrice || !maxPrice || !numBuyOrders || !numSellOrders || !quantityPerOrder) isValid = false;
            command += ` --symbol ${gridSymbol} --min-price ${minPrice} --max-price ${maxPrice} --num-buy-orders ${numBuyOrders} --num-sell-orders ${numSellOrders} --quantity-per-order ${quantityPerOrder}`;
            break;
        case 'check-balance':
            // 'check-balance' command does not require any additional arguments.
            break;
        default:
            // If no valid command type is selected, set isValid to false.
            isValid = false;
            break;
    }

    // Display the generated command or an error message.
    if (!isValid) {
        generatedCommandPre.textContent = "Please fill all required fields.";
        generatedCommandPre.classList.add('text-red-400'); // Add red text for error.
    } else {
        generatedCommandPre.textContent = command;
        generatedCommandPre.classList.remove('text-red-400'); // Remove red text if previously set.
        commandOutputDiv.classList.remove('hidden'); // Show the command output div.
    }
}

// 5. Function to copy the generated command to clipboard:
// This function handles copying the text content of 'generatedCommandPre' to the user's clipboard.
function copyCommand() {
    const commandText = generatedCommandPre.textContent;
    // Only attempt to copy if there's valid text.
    if (commandText && commandText !== "Please fill all required fields.") {
        // document.execCommand('copy') is used here for broader compatibility, especially within iframes.
        // navigator.clipboard.writeText() is the modern API, but can have restrictions in certain embedded contexts.
        document.execCommand('copy'); 
        
        // Show the "Copied to clipboard!" message and then hide it after 2 seconds.
        copyMessageP.classList.remove('hidden');
        setTimeout(() => copyMessageP.classList.add('hidden'), 2000); // 2000ms = 2 seconds.
    }
}

// 6. Function to display log content from textarea:
// This function takes the text pasted into 'logInputTextarea' and displays it in 'logOutputDiv'.
function displayLog() {
    const logContent = logInputTextarea.value;
    // Check if the textarea is empty.
    if (logContent.trim() === "") { // .trim() removes leading/trailing whitespace.
        logOutputDiv.textContent = "No log content to display. Please paste content from bot.log.";
        logOutputDiv.classList.add('text-red-400'); // Add red text for error.
    } else {
        logOutputDiv.textContent = logContent;
        logOutputDiv.classList.remove('text-red-400'); // Remove red text if previously set.
        logOutputDiv.classList.remove('hidden'); // Show the log output div.
    }
}

// 7. Event Listeners:
// Event listeners are functions that wait for a specific event to happen (e.g., a click, a change)
// and then execute a piece of code.
document.addEventListener('DOMContentLoaded', () => {
    // 'DOMContentLoaded' event fires when the initial HTML document has been completely loaded and parsed,
    // without waiting for stylesheets, images, and subframes to finish loading.
    // This is a good place to put code that interacts with the DOM, ensuring all elements are available.

    // Attach the 'showOrderForm' function to the 'change' event of the 'orderTypeSelect' dropdown.
    orderTypeSelect.addEventListener('change', showOrderForm);
    
    // Attach the 'copyCommand' function to the 'click' event of the 'copyBtn'.
    copyBtn.addEventListener('click', copyCommand); 
    
    // Attach the 'displayLog' function to the 'click' event of the 'displayLogBtn'.
    displayLogBtn.addEventListener('click', displayLog);
    
    // Initialize the form display when the page first loads.
    showOrderForm();
});

// 8. Global copy event listener for execCommand:
// This is a fallback mechanism for the copy functionality, particularly useful in environments like iframes
// where direct clipboard access might be restricted. It intercepts the 'copy' event.
document.addEventListener('copy', (e) => {
    const commandText = generatedCommandPre.textContent;
    if (commandText && commandText !== "Please fill all required fields.") {
        // Set the data to be copied to the clipboard.
        e.clipboardData.setData('text/plain', commandText);
        // Prevent the browser's default copy action, as we're handling it manually.
        e.preventDefault(); 
    }
});