// data/model/Message.kt
package com.zappiesai.chatbot.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.Date

@Entity(tableName = "messages")
data class Message(
    @PrimaryKey
    val id: String,
    val conversationId: String,
    val content: String,
    val senderType: SenderType,
    val timestamp: Date,
    val isRead: Boolean = false,
    val isSent: Boolean = true,
    val metadata: Map<String, Any>? = null
)

enum class SenderType {
    USER, BOT, SYSTEM
}
