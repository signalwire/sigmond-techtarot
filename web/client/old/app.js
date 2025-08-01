// Initialize the call widget
document.addEventListener('DOMContentLoaded', function() {
    // Set the button text
    document.getElementById('callButton').textContent = 'Call Sigmond';
    
    // Get the widget
    const widget = document.querySelector("call-widget");
    
    // Set user variables for the widget
    widget.setUserVariables({extension: "sigmond_tarot"});
    
    // Listen for user events from the widget
    widget.on('user_event', (params) => {
        console.log('User event received:', params);
        
        // Handle tarot card display events
        if (params && params.detail && params.detail.type === 'show_tarot_cards') {
            console.log('Tarot cards received!');
            console.log('Reading data:', params.detail.reading);
            
            // Log each card for debugging
            console.log('Past card:', params.detail.reading.past);
            console.log('Present card:', params.detail.reading.present);
            console.log('Future card:', params.detail.reading.future);
            
            // We'll add card display logic here later
            displayTarotCards(params.detail.reading);
        }
    });
    
    // Function to display tarot cards (placeholder for now)
    function displayTarotCards(reading) {
        console.log('displayTarotCards called with:', reading);
        // TODO: Implement card display UI
    }
});