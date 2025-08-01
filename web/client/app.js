// Configuration
const DESTINATION = '/public/tony-s-swml-generator';
// REPLACE THIS WITH YOUR ACTUAL SIGNALWIRE TOKEN
const STATIC_TOKEN = 'eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIiwiY2giOiJwdWMuc3dpcmUuaW8iLCJ0eXAiOiJTQVQifQ..ldlG2mqOLIrR0y0w.2bYZGJwmtZxqNj9lZ2Xeh-H-Rxg05mIjKQk0lldUK2aCvRzu_aAbMPqDJbMSvbW7fCQ019o-ZWVmMWJNZvCLP2EROqy1X7bgySgnMCRBg_Eny3y41DuZxznGA85WTKyxCXTXsUWtid2OtaQP-2cR_yG92gIRxe_FMil5yD6plfL_ksU8nIYhNjGKW-MT8MoTanrcduVj7pPYLlLxRofnI9pgN8uL6S-yYNpFjLcmVcDAHS83pAXuq5SHFuIoVMqmuMfaMhiB8TjDlqUHWRmAviItIHBzD5rkK_ZSn5gPsCO2G4OJbCfOY6_0MwL5h8DK94GhscTlSdHcvFKVFl-EbOB8yXljLUUaENjihdiwK7b21SzDVAceYqt9emvcBOk-3nh7_ih1hgYqSnOpAdK34Gled4WuIApJGtqfTBIew4_SKF4Y0GXrzR39Fy3HZ5i9dvwR3vU_jl5-e2leRMokwTyElHrvm4VhUUe8VZoyN2vQjLRTAaRqq1hUZaAW2muOFFPLNcJL8uixiO2k.rRwkRKiVYz620NnCx2jIVw';
const BASE_URL = 'https://tatooine.cantina.cloud/devuser/tarot';

let client;
let roomSession;
let cardsRevealed = false;
let isMuted = false;
const cards = {
    past: null,
    present: null,
    future: null
};

// UI Elements
const connectBtn = document.getElementById('connectBtn');
const hangupBtn = document.getElementById('hangupBtn');
const muteBtn = document.getElementById('muteBtn');
const startMutedCheckbox = document.getElementById('startMuted');
const showLogCheckbox = document.getElementById('showLog');
const statusDiv = document.getElementById('status');
const eventLog = document.getElementById('event-log');
const eventLogHeader = document.getElementById('event-log-header');
const eventEntries = document.getElementById('event-entries');

// Event logging with circular reference handling
function logEvent(message, data = null, isUserEvent = false) {
    const entry = document.createElement('div');
    entry.className = isUserEvent ? 'event-entry user-event' : 'event-entry';
    const time = new Date().toLocaleTimeString();
    
    let dataStr = '';
    if (data) {
        try {
            // Handle circular references
            const seen = new WeakSet();
            dataStr = JSON.stringify(data, (key, value) => {
                if (typeof value === 'object' && value !== null) {
                    if (seen.has(value)) {
                        return '[Circular Reference]';
                    }
                    seen.add(value);
                }
                return value;
            }, 2);
        } catch (e) {
            dataStr = 'Error serializing data: ' + e.message;
        }
    }
    
    entry.innerHTML = `
        <div class="event-time">${time}</div>
        <div>${isUserEvent ? '🔴 USER EVENT: ' : ''}${message}</div>
        ${dataStr ? `<div style="color: #888; margin-left: 10px;">${dataStr}</div>` : ''}
    `;
    eventEntries.appendChild(entry);
    eventEntries.scrollTop = eventEntries.scrollHeight;
}

// Initialize SignalWire client (without dialing)
async function initializeClient() {
    try {
        statusDiv.textContent = 'Ready to connect';
        logEvent('Client ready - click Connect to dial');
        
    } catch (error) {
        logEvent('Initialization error', { error: error.message });
        statusDiv.textContent = 'Initialization failed';
    }
}

// Connect to call with static token
async function connectToCall() {
    try {
        // Clear previous event log entries
        eventEntries.innerHTML = '';
        logEvent('Starting new connection...');
        
        if (!STATIC_TOKEN || STATIC_TOKEN === 'YOUR_SIGNALWIRE_TOKEN_HERE') {
            throw new Error('Please update STATIC_TOKEN with your actual SignalWire token');
        }
        
        statusDiv.textContent = 'Initializing client...';
        logEvent('Using static token', { tokenLength: STATIC_TOKEN.length });

        // Initialize client with debug options
        // SignalWire should be available on window when using UMD build
        const SignalWireSDK = window.SignalWire || SignalWire;
        logEvent('SignalWire SDK check', { 
            hasWindow: typeof window !== 'undefined',
            hasSignalWire: typeof SignalWire !== 'undefined',
            hasWindowSignalWire: typeof window.SignalWire !== 'undefined',
            SignalWireType: typeof SignalWireSDK,
            SignalWireKeys: SignalWireSDK ? Object.keys(SignalWireSDK) : []
        });

        // Based on the keys, we need to use Fabric
        if (typeof SignalWireSDK.Fabric === 'function') {
            client = await SignalWireSDK.Fabric({
                token: STATIC_TOKEN,
                logLevel: 'debug',
                debug: { logWsTraffic: false }
            });
        } else if (typeof SignalWireSDK.SignalWire === 'function') {
            client = await SignalWireSDK.SignalWire({
                token: STATIC_TOKEN,
                logLevel: 'debug',
                debug: { logWsTraffic: false }
            });
        } else {
            throw new Error('SignalWire SDK not found or not a function');
        }

        logEvent('Client initialized');

        // Subscribe to ALL events on the client to debug
        const originalEmit = client.emit;
        client.emit = function(event, ...args) {
            if (event !== 'signalwire.socket.message' && event !== 'signalwire.socket.open') {
                logEvent(`Client event: ${event}`, args[0]);
            }
            return originalEmit.apply(this, [event, ...args]);
        };

        // Try multiple event patterns
        client.on('user_event', (params) => {
            console.log('🔴 CLIENT EVENT: user_event (no prefix)', params);
            logEvent('user_event (no prefix)', params, true);
            handleUserEvent(params);
        });

        client.on('calling.user_event', (params) => {
            console.log('🟠 CLIENT EVENT: calling.user_event', params);
            logEvent('calling.user_event', params, true);
            handleUserEvent(params);
        });

        client.on('signalwire.event', (params) => {
            console.log('🟡 CLIENT EVENT: signalwire.event', params);
            if (params.event_type === 'user_event') {
                console.log('✅ Found user_event in signalwire.event!', params.params);
                logEvent('Found user_event in signalwire.event', params.params, true);
                handleUserEvent(params.params || params);
            } else {
                logEvent('signalwire.event', params);
            }
        });

        statusDiv.textContent = 'Dialing...';
        
        // Dial into the room
        roomSession = await client.dial({
            to: DESTINATION,
            rootElement: document.getElementById('video-container'),
            audio: true,
            video: true,
            negotiateVideo: true,
            userVariables: {
                userName: 'Tarot Reader',
                interface: 'raw-sdk-static',
                timestamp: new Date().toISOString(),
                extension: 'sigmond_tarot'
            }
        });

        logEvent('Dial initiated');

        // Subscribe to room session events
        roomSession.on('room.started', (params) => {
            logEvent('room.started', params);
        });

        roomSession.on('call.joined', (params) => {
            logEvent('call.joined', params);
            statusDiv.textContent = 'Connected to Sigmond';
            connectBtn.style.display = 'none';
            hangupBtn.style.display = 'inline-block';
            muteBtn.style.display = 'inline-block';
            
            // Hide the deck placeholder
            const deckPlaceholder = document.getElementById('deck-placeholder');
            if (deckPlaceholder) {
                deckPlaceholder.style.display = 'none';
            }
        });

        roomSession.on('member.joined', (params) => {
            logEvent('member.joined', params);
        });

        roomSession.on('member.left', (params) => {
            logEvent('member.left', params);
        });

        roomSession.on('room.left', (params) => {
            logEvent('room.left', params);
            handleDisconnect();
        });

        roomSession.on('destroy', (params) => {
            logEvent('destroy', params);
            handleDisconnect();
        });

        // Watch for when localStream becomes available
        const checkLocalStream = setInterval(() => {
            if (roomSession && roomSession.localStream) {
                clearInterval(checkLocalStream);
                logEvent('Local stream found');
                
                const audioTracks = roomSession.localStream.getAudioTracks();
                
                // Disable AGC on audio tracks
                audioTracks.forEach(track => {
                    // Apply constraints to disable AGC
                    track.applyConstraints({
                        autoGainControl: false,
                        echoCancellation: true,
                        noiseSuppression: true
                    }).then(() => {
                        logEvent(`Disabled AGC on audio track: ${track.label}`);
                    }).catch(err => {
                        logEvent(`Failed to disable AGC: ${err.message}`);
                    });
                });
                
                // Check if we should start muted
                if (startMutedCheckbox.checked) {
                    audioTracks.forEach(track => {
                        track.enabled = false;
                        logEvent(`Muted audio track: ${track.label}`);
                    });
                    isMuted = true;
                    muteBtn.textContent = 'Unmute';
                    logEvent('Started call muted as requested');
                }
            }
        }, 50); // Check every 50ms
        
        // Store interval for cleanup
        roomSession._streamCheckInterval = checkLocalStream;

        // Note: user_event comes through the client, not roomSession
        // Commenting out roomSession listener as per user guidance
        /*
        roomSession.on('user_event', (params) => {
            console.log('🟢 ROOMSESSION EVENT: user_event', params);
            logEvent('user_event on roomSession', params);
            handleUserEvent(params);
        });
        */

        // Monitor all roomSession events
        const originalRoomEmit = roomSession.emit;
        roomSession.emit = function(event, ...args) {
            if (!event.includes('member.updated') && event !== 'call.joined') {
                // Log only safe properties to avoid circular references
                const safeData = args[0] ? {
                    type: args[0].type,
                    event_type: args[0].event_type,
                    params: args[0].params,
                    // Add other safe properties as needed
                    hasCallObject: !!args[0].call,
                    hasMemberObject: !!args[0].member
                } : args[0];
                logEvent(`RoomSession event: ${event}`, safeData);
            }
            return originalRoomEmit.apply(this, [event, ...args]);
        };
        
        // Start the call - this might be needed based on the widget code
        logEvent('Starting call...');
        await roomSession.start();
        
    } catch (error) {
        logEvent('Connection error', { error: error.message, stack: error.stack });
        statusDiv.textContent = 'Connection failed';
        connectBtn.style.display = 'inline-block';
        hangupBtn.style.display = 'none';
    }
}

function handleDisconnect() {
    // Clean up stream check interval
    if (roomSession && roomSession._streamCheckInterval) {
        clearInterval(roomSession._streamCheckInterval);
    }
    
    // Clean up client
    if (client) {
        client.disconnect();
        client = null;
    }
    roomSession = null;
    statusDiv.textContent = 'Disconnected';
    connectBtn.style.display = 'inline-block';
    hangupBtn.style.display = 'none';
    muteBtn.style.display = 'none';
    muteBtn.textContent = 'Mute';
    isMuted = false;
    clearCards();
    
    // Show the deck placeholder again
    const deckPlaceholder = document.getElementById('deck-placeholder');
    if (deckPlaceholder) {
        deckPlaceholder.style.display = 'block';
    }
    
    logEvent('Disconnected - ready for new connection');
}

async function hangup() {
    if (roomSession) {
        try {
            await roomSession.hangup();
        } catch (e) {
            logEvent('Hangup error', { error: e.message });
        }
    }
    handleDisconnect();
}

function handleUserEvent(eventData) {
    logEvent('Processing user event', eventData, true);
    
    // Also log to console for debugging
    console.log('🎯 USER EVENT RECEIVED IN HANDLER:');
    console.log('Event Data:', eventData);
    console.log('Event Type:', eventData?.type);
    console.log('Event Payload:', eventData?.payload);
    console.log('Full Event Object:', JSON.stringify(eventData, null, 2));
    console.log('----------------------------');
    
    if (eventData.type === 'show_tarot_cards' && eventData.reading) {
        console.log('📋 Showing tarot cards:', eventData.reading);
        logEvent('Showing tarot cards', null, true);
        if (!cardsRevealed) {
            revealCardArea();
        }
        setTimeout(() => {
            dealCards(eventData.reading);
        }, cardsRevealed ? 0 : 800);
    } else if (eventData.type === 'flip_card') {
        console.log('🔄 Flipping card:', eventData.position);
        logEvent(`Flipping ${eventData.position} card`, null, true);
        flipCard(eventData.position);
    } else if (eventData.type === 'clear_cards') {
        console.log('🧹 Clearing cards');
        logEvent('Clearing cards', null, true);
        clearCards();
    } else {
        console.log('❓ Unknown user event type:', eventData.type);
        logEvent(`Unknown event type: ${eventData.type}`, null, true);
    }
}

function dealCards(reading) {
    const positions = ['past', 'present', 'future'];
    
    positions.forEach((position, index) => {
        setTimeout(() => {
            if (reading[position]) {
                createCard(position, reading[position]);
                // Automatically flip the card after a short delay
                setTimeout(() => {
                    flipCard(position);
                }, 400);
            }
        }, index * 600);
    });
}

function createCard(position, cardData) {
    const slot = document.getElementById(`${position}-slot`);
    const placeholder = slot.querySelector('.card-placeholder');
    
    // Remove existing card if present
    const existingCard = document.getElementById(`${position}-card`);
    if (existingCard) {
        existingCard.remove();
    }
    
    cards[position] = cardData;
    
    // Log card data for debugging
    logEvent(`Creating ${position} card`, {
        name: cardData.name,
        image: cardData.image,
        reversed: cardData.reversed
    });
    
    const card = document.createElement('div');
    card.className = 'tarot-card dealing';
    card.id = `${position}-card`;
    
    const cardBack = document.createElement('div');
    cardBack.className = 'card-face card-back';
    
    const cardFront = document.createElement('div');
    cardFront.className = 'card-face card-front';
    
    // Construct the full image URL
    const imageUrl = cardData.image.startsWith('http') ? cardData.image : `${BASE_URL}/${cardData.image}`;
    
    // Log the constructed URL
    logEvent(`Image URL for ${position}`, { url: imageUrl });
    
    // Apply rotation if card is reversed (upside down) - combine with scale
    const imageStyle = cardData.reversed ? 'transform: scale(1.06) rotate(180deg);' : '';
    
    cardFront.innerHTML = `
        <img class="card-image${cardData.reversed ? ' reversed' : ''}" src="${imageUrl}" alt="${cardData.name}" style="${imageStyle}" 
             onload="console.log('Image loaded:', '${imageUrl}')"
             onerror="console.log('Image failed:', '${imageUrl}'); this.src='data:image/svg+xml,%3Csvg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"150\" viewBox=\"0 0 100 150\"%3E%3Crect width=\"100\" height=\"150\" fill=\"%23ddd\"%2F%3E%3Ctext x=\"50\" y=\"75\" text-anchor=\"middle\" fill=\"%23666\" font-size=\"12\"%3E${encodeURIComponent(cardData.name)}%3C/text%3E%3C/svg%3E'">
    `;
    
    card.appendChild(cardBack);
    card.appendChild(cardFront);
    
    placeholder.style.display = 'none';
    slot.appendChild(card);
}

function flipCard(position) {
    const card = document.getElementById(`${position}-card`);
    if (card) {
        // Toggle the flip state
        card.classList.toggle('flipped');
    }
}

function revealCardArea() {
    const tarotTable = document.getElementById('tarot-table');
    const videoContainer = document.getElementById('video-container');
    
    tarotTable.classList.remove('hidden');
    tarotTable.classList.add('visible');
    videoContainer.classList.add('with-cards');
    cardsRevealed = true;
}

function hideCardArea() {
    const tarotTable = document.getElementById('tarot-table');
    const videoContainer = document.getElementById('video-container');
    
    tarotTable.classList.remove('visible');
    tarotTable.classList.add('hidden');
    videoContainer.classList.remove('with-cards');
    cardsRevealed = false;
}

function clearCards() {
    ['past', 'present', 'future'].forEach(position => {
        const slot = document.getElementById(`${position}-slot`);
        const card = document.getElementById(`${position}-card`);
        const placeholder = slot.querySelector('.card-placeholder');
        
        if (card) {
            card.remove();
        }
        if (placeholder) {
            placeholder.style.display = 'flex';
        }
        
        cards[position] = null;
    });
    setTimeout(() => {
        hideCardArea();
    }, 1000);
}

// Mute/unmute functions
function toggleMute() {
    try {
        // The localStream should be stored on the roomSession
        if (roomSession && roomSession.localStream) {
            const audioTracks = roomSession.localStream.getAudioTracks();
            
            // Toggle each audio track
            audioTracks.forEach(track => {
                track.enabled = !track.enabled;
                logEvent(`Audio track ${track.label} enabled: ${track.enabled}`);
            });
            
            // Update UI based on first track state
            if (audioTracks.length > 0) {
                isMuted = !audioTracks[0].enabled;
                muteBtn.textContent = isMuted ? 'Unmute' : 'Mute';
                logEvent(isMuted ? 'Microphone muted' : 'Microphone unmuted');
            }
        } else {
            logEvent('No local stream found on roomSession');
        }
    } catch (error) {
        logEvent('Mute toggle error', { error: error.message });
    }
}

// Event listeners
connectBtn.addEventListener('click', connectToCall);
hangupBtn.addEventListener('click', hangup);
muteBtn.addEventListener('click', toggleMute);

// Toggle event log visibility based on checkbox
showLogCheckbox.addEventListener('change', () => {
    if (showLogCheckbox.checked) {
        eventLog.style.display = 'block';
    } else {
        eventLog.style.display = 'none';
    }
});

// Toggle event log collapsed state
eventLogHeader.addEventListener('click', () => {
    eventLog.classList.toggle('collapsed');
});

// Initialize on load (but don't connect)
window.addEventListener('load', () => {
    logEvent('Page loaded');
    initializeClient();
});