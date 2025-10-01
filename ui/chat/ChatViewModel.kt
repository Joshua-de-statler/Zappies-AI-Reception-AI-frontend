// ui/chat/ChatViewModel.kt
package com.zappiesai.chatbot.ui.chat

import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.zappiesai.chatbot.data.model.Message
import com.zappiesai.chatbot.data.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val chatRepository: ChatRepository
    // You can also inject an AuthRepository to get the user's token and details
) : ViewModel() {

    // This holds the list of messages. It's a private mutable state...
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    // ...and this is the public, unchangeable version the UI will observe.
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    // Holds the current text in the message input field.
    private val _messageText = mutableStateOf("")
    val messageText: State<String> = _messageText

    // This would be fetched dynamically after the user logs in.
    private val conversationId = "user_conversation_123"

    init {
        // When the ViewModel is created, start listening for messages from the database.
        viewModelScope.launch {
            chatRepository.getMessages(conversationId).collect { messageList ->
                _messages.value = messageList
            }
        }
        // Connect to the WebSocket to receive real-time updates.
        // The token would come from your secure storage.
        chatRepository.connectWebSocket("your_jwt_token")
    }

    fun onMessageTextChanged(newText: String) {
        _messageText.value = newText
    }

    fun sendMessage() {
        if (messageText.value.isNotBlank()) {
            viewModelScope.launch {
                chatRepository.sendMessage(conversationId, messageText.value)
                // Clear the input field immediately for a snappy feel.
                _messageText.value = ""
            }
        }
    }

    // It's crucial to disconnect when the ViewModel is destroyed to avoid memory leaks.
    override fun onCleared() {
        super.onCleared()
        chatRepository.disconnectWebSocket()
    }
}