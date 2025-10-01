// data/repository/ChatRepository.kt
package com.zappiesai.chatbot.data.repository

import com.zappiesai.chatbot.data.api.ChatApi
import com.zappiesai.chatbot.data.database.MessageDao
import com.zappiesai.chatbot.data.model.Message
import com.zappiesai.chatbot.data.websocket.WebSocketManager
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val chatApi: ChatApi,
    private val messageDao: MessageDao,
    private val webSocketManager: WebSocketManager
    // In a real app, you would also inject a secure preferences manager to get the token
) {

    /**
     * Gets a real-time stream of messages from the local database.
     * The UI will automatically update whenever a new message is inserted.
     */
    fun getMessages(conversationId: String): Flow<List<Message>> {
        return messageDao.getMessagesForConversation(conversationId)
    }

    /**
     * Sends a message to the backend API.
     * This is a "fire-and-forget" call; the API will respond with 202 Accepted,
     * and the bot's reply will arrive later via WebSocket.
     */
    suspend fun sendMessage(conversationId: String, content: String) {
        // In a real app, the token would be retrieved from a secure storage.
        val token = "your_jwt_access_token"
        val messageRequest = mapOf(
            "conversation_id" to conversationId,
            "message" to content
        )
        chatApi.sendMessage("Bearer $token", messageRequest)
    }

    /**
     * Connects to the WebSocket server and listens for incoming messages.
     * When a message arrives, it's saved to the local database, which automatically
     * updates the UI thanks to the Flow from getMessages().
     */
    fun connectWebSocket(token: String) {
        webSocketManager.connect(token) { incomingMessage ->
            // This is a callback lambda that executes when a message arrives.
            // We simply save it, and the rest of the app reacts automatically.
            // You'll need a CoroutineScope to launch this suspend function.
            // For example: scope.launch { messageDao.insertMessage(incomingMessage) }
        }
    }

    fun disconnectWebSocket() {
        webSocketManager.disconnect()
    }
}