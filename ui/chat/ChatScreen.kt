// ui/chat/ChatScreen.kt
package com.zappiesai.chatbot.ui.chat

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.zappiesai.chatbot.data.model.Message
import com.zappiesai.chatbot.data.model.SenderType

@Composable
fun ChatScreen(
    viewModel: ChatViewModel = hiltViewModel()
) {
    // These lines subscribe the UI to the ViewModel's state.
    // Whenever messages or messageText changes, this Composable will automatically redraw.
    val messages by viewModel.messages.collectAsState()
    val messageText by viewModel.messageText
    val listState = rememberLazyListState()

    // Automatically scroll to the bottom when a new message arrives.
    LaunchedEffect(messages) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Zappies AI Assistant") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
                contentPadding = PaddingValues(vertical = 8.dp)
            ) {
                items(messages) { message ->
                    MessageBubble(message = message)
                }
            }
            MessageInput(
                text = messageText,
                onTextChanged = viewModel::onMessageTextChanged,
                onSendClicked = viewModel::sendMessage
            )
        }
    }
}

@Composable
fun MessageBubble(message: Message) {
    val horizontalArrangement = if (message.senderType == SenderType.USER) Arrangement.End else Arrangement.Start
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = horizontalArrangement
    ) {
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (message.senderType == SenderType.USER) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier.widthIn(max = 300.dp) // Prevent bubbles from stretching too wide
        ) {
            Text(
                text = message.content,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
            )
        }
    }
}

@Composable
fun MessageInput(text: String, onTextChanged: (String) -> Unit, onSendClicked: () -> Unit) {
    Surface(shadowElevation = 8.dp) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextField(
                value = text,
                onValueChange = onTextChanged,
                modifier = Modifier.weight(1f),
                placeholder = { Text("Type a message...") },
                colors = TextFieldDefaults.colors(
                    focusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                    unfocusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent
                )
            )
            Spacer(Modifier.width(8.dp))
            Button(onClick = onSendClicked, enabled = text.isNotBlank()) {
                Text("Send")
            }
        }
    }
}