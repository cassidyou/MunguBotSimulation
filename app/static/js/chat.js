let socket;
let chatRole;
let chatId;

// Create chatClient object to match template expectations
window.chatClient = {
    init: function(config) {
        chatId = config.chatId;
        chatRole = config.role;
        const token = config.token || '';
        // Build WebSocket URL with proper parameters
        let wsUrl = `ws://${window.location.host}/ws/chat/${chatId}?role=${chatRole}`;
        if (token) {
            wsUrl += `&token=${encodeURIComponent(token)}`;
        }
        console.log(`Connecting to WebSocket: ${wsUrl}`);
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log("Connected to chat");
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("Received message:", data);
                if (data.type === "history") {
                    // Load chat history
                    data.messages.forEach(msg => {
                        appendMessage(msg.sender, msg.content);
                    });
                } else if (data.type === "message") {
                    // New message
                    appendMessage(data.message.sender, data.message.content);
                }
            } catch (e) {
                console.error("Error parsing message:", e);
            }
        };

        socket.onclose = () => {
            console.log("Disconnected from chat");
        };
        
        socket.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
    },
    
    send: function(messageData) {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.error("WebSocket not connected");
            return;
        }
        
        try {
            socket.send(JSON.stringify(messageData));
            console.log("Sent message:", messageData);
        } catch (e) {
            console.error("Error sending message:", e);
        }
    }
};

function initChatSocket(chatIdParam, role, token = '') {
    chatRole = role;
    chatId = chatIdParam;
    // Build WebSocket URL with proper parameters
    let wsUrl = `ws://${window.location.host}/ws/chat/${chatId}?role=${role}`;
    if (token) {
        wsUrl += `&token=${encodeURIComponent(token)}`;
    }
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log("Connected to chat");
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("Received message:", data);
            if (data.type === "history") {
                // Load chat history
                data.messages.forEach(msg => {
                    appendMessage(msg.sender, msg.content);
                });
            } else if (data.type === "message") {
                // New message
                appendMessage(data.message.sender, data.message.content);
            }
        } catch (e) {
            console.error("Error parsing message:", e);
        }
    };

    socket.onclose = () => {
        console.log("Disconnected from chat");
    };
    
    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
    };
}

function sendMessage() {
    const input = document.getElementById("textarea-id");
    const message = input.value.trim();
    if (message === "" || !socket || socket.readyState !== WebSocket.OPEN) {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.error("WebSocket not connected");
        }
        return;
    }

    // Send message in the expected format
    const messageData = {
        sender: chatRole,
        content: message
    };
    
    try {
        socket.send(JSON.stringify(messageData));
        console.log("Sent message:", messageData);
        // Clear input but don't append message here, let the broadcast handle it
        input.value = "";
    } catch (e) {
        console.error("Error sending message:", e);
    }
}

function appendMessage(sender, message) {
    // Try to find the message container by ID first, then by data-testid
    let container = document.getElementById("messageList");
    let scrollable = document.getElementById("scrollable");
    if (!container) {
        container = document.querySelector('[data-testid="messagesList"]');
    }
    if (!container) {
        console.error("Message container not found");
        return;
    }
    
    const div = document.createElement("div");

    if (sender === "admin") {
        div.innerHTML = `
            <div
            data-v-110db55e=""
            data-v-ca02f5f2=""
            >
            <div
                data-v-110db55e=""
                class="d-flex flex-column py-1 align-start pt-2"
                data-testid="messageItem"
            >
                <div
                data-v-110db55e=""
                class="d-flex align-center mx-4 mb-1 flex-row"
                >
                <div
                    data-v-110db55e=""
                    data-testid="messageBulb-6a07eaddd59f42529deb"
                    class="px-4 py-2 message-blob d-flex flex-column relative message-customer"
                >
                    <!----><!----><span
                    data-v-110db55e=""
                    class="message-content"
                    >
                    ${escapeHtml(message)}
                    </span>
                </div>
                <div
                    data-v-110db55e=""
                    class="d-flex"
                >
                    <button
                    data-v-110db55e=""
                    type="button"
                    class="mx-2 v-btn v-btn--fab v-btn--has-bg v-btn--round theme--light elevation-0 v-size--small blue-grey lighten-5"
                    data-testid="openReportDialog"
                    >
                    <span class="v-btn__content"
                        ><i
                        data-v-110db55e=""
                        aria-hidden="true"
                        class="v-icon notranslate mdi mdi-alert theme--light blue-grey--text text--lighten-4"
                        style="font-size: 16px"
                        ></i
                    ></span>
                    </button>
                </div>
                </div>
                <div
                data-v-110db55e=""
                class="d-inline-flex align-baseline justify-space-between mx-4 opacity-50"
                style="gap: 0.1rem 0.5rem"
                >
                <!---->
                <div
                    data-v-110db55e=""
                    class="d-inline-flex align-baseline justify-start"
                    style="gap: 0.1rem 0.5rem"
                >
                    <!----><!----><span
                    data-v-110db55e=""
                    class="caption compact-line-height created-at text-left"
                    style="flex: 1 0 auto"
                    ><span
                        data-v-110db55e=""
                        style="width: max-content"
                        ><strong
                        class="blue--text text--darken-2"
                        ></strong
                        ></span
                    ></span
                    ><!---->
                </div>
                </div>
            </div>
            <div
                data-v-110db55e=""
                class="v-dialog__container"
            >
                <!---->
            </div>
            </div>
        
        `;
    } else {
        div.innerHTML = `
       
            <div
            data-v-110db55e=""
            data-v-ca02f5f2=""
            >
            <div
                data-v-110db55e=""
                class="d-flex flex-column py-1 align-end pt-2"
                data-testid="messageItem"
            >
                <div
                data-v-110db55e=""
                class="d-flex align-center mx-4 mb-1 flex-row-reverse"
                >
                <div
                    data-v-110db55e=""
                    data-testid="messageBulb-8731d54b17b04e939578"
                    class="px-4 py-2 message-blob d-flex flex-column relative message-profile"
                >
                    <!----><!----><span
                    data-v-110db55e=""
                    class="message-content"
                    >
                    ${escapeHtml(message)}
                    </span>
                </div>
                <div
                    data-v-110db55e=""
                    class="d-flex"
                >
                    <button
                    data-v-110db55e=""
                    type="button"
                    class="mx-2 v-btn v-btn--fab v-btn--has-bg v-btn--round theme--light elevation-0 v-size--small blue-grey lighten-5"
                    data-testid="openReportDialog"
                    >
                    <span class="v-btn__content"
                        ><i
                        data-v-110db55e=""
                        aria-hidden="true"
                        class="v-icon notranslate mdi mdi-alert theme--light blue-grey--text text--lighten-4"
                        style="font-size: 16px"
                        ></i
                    ></span>
                    </button>
                </div>
                </div>
                <div
                data-v-110db55e=""
                class="d-inline-flex align-baseline justify-space-between mx-4 opacity-50"
                style="gap: 0.1rem 0.5rem"
                >
                <!---->
                <div
                    data-v-110db55e=""
                    class="d-inline-flex align-baseline justify-end"
                    style="gap: 0.1rem 0.5rem"
                >
                    <!----><!----><span
                    data-v-110db55e=""
                    class="caption compact-line-height created-at text-right"
                    style="flex: 1 0 auto"
                    ><span
                        data-v-110db55e=""
                        style="width: max-content"
                        ><strong
                        class="blue--text text--darken-2"
                        >User</strong
                        ></span
                    ></span
                    ><!---->
                </div>
                </div>
            </div>
            <div
                data-v-110db55e=""
                class="v-dialog__container"
            >
                <!---->
            </div>
            </div>
       
    `;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// Utility function to escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}