// app/build.gradle.kts
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("kotlin-kapt")
    id("dagger.hilt.android.plugin")
    id("kotlin-parcelize")
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
}

android {
    namespace = "com.zappiesai.chatbot"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.zappiesai.chatbot"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        
        buildConfigField("String", "BASE_URL", "\"https://api.zappies-ai.com/\"")
        buildConfigField("String", "WEBSOCKET_URL", "\"wss://ws.zappies-ai.com/\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
}

dependencies {
    // Core Android
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")
    
    // Jetpack Compose
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    
    // Navigation
    implementation("androidx.navigation:navigation-compose:2.7.7")
    
    // Dependency Injection
    implementation("com.google.dagger:hilt-android:2.48")
    kapt("com.google.dagger:hilt-compiler:2.48")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")
    
    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    
    // WebSocket
    implementation("org.java-websocket:Java-WebSocket:1.5.4")
    
    // Database
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")
    
    // Security
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    
    // Image Loading
    implementation("io.coil-kt:coil-compose:2.5.0")
    
    // Firebase
    implementation(platform("com.google.firebase:firebase-bom:32.7.1"))
    implementation("com.google.firebase:firebase-analytics")
    implementation("com.google.firebase:firebase-crashlytics")
    implementation("com.google.firebase:firebase-messaging")
    
    // DataStore
    implementation("androidx.datastore:datastore-preferences:1.0.0")
    
    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}

// data/model/User.kt
package com.zappiesai.chatbot.data.model

import kotlinx.parcelize.Parcelize
import android.os.Parcelable

@Parcelize
data class User(
    val id: Int,
    val uuid: String,
    val email: String,
    val phone: String,
    val name: String,
    val companyName: String? = null,
    val avatarUrl: String? = null,
    val bio: String? = null,
    val industry: String? = null,
    val isVerified: Boolean = false,
    val subscriptionTier: String = "free",
    val createdAt: String? = null
) : Parcelable

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

// data/repository/ChatRepository.kt
package com.zappiesai.chatbot.data.repository

import com.zappiesai.chatbot.data.api.ChatApi
import com.zappiesai.chatbot.data.database.MessageDao
import com.zappiesai.chatbot.data.model.Message
import com.zappiesai.chatbot.data.websocket.WebSocketManager
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val chatApi: ChatApi,
    private val messageDao: MessageDao,
    private val webSocketManager: WebSocketManager
) {
    
    fun getMessages(conversationId: String): Flow<List<Message>> {
        return messageDao.getMessagesForConversation(conversationId)
    }
    
    suspend fun sendMessage(conversationId: String, content: String): Result<Message> {
        return try {
            // Send via API
            val response = chatApi.sendMessage(
                mapOf(
                    "conversation_id" to conversationId,
                    "message" to content
                )
            )
            
            // Save to local database
            val message = Message(
                id = response.messageId,
                conversationId = conversationId,
                content = content,
                senderType = SenderType.USER,
                timestamp = Date()
            )
            messageDao.insertMessage(message)
            
            // Also send via WebSocket for real-time sync
            webSocketManager.sendMessage(message)
            
            Result.success(message)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    fun connectWebSocket() {
        webSocketManager.connect()
    }
    
    fun disconnectWebSocket() {
        webSocketManager.disconnect()
    }
}

// di/AppModule.kt
package com.zappiesai.chatbot.di

import android.content.Context
import com.zappiesai.chatbot.BuildConfig
import com.zappiesai.chatbot.data.api.ChatApi
import com.zappiesai.chatbot.data.api.AuthApi
import com.zappiesai.chatbot.data.database.AppDatabase
import com.zappiesai.chatbot.data.database.MessageDao
import com.zappiesai.chatbot.data.websocket.WebSocketManager
import com.zappiesai.chatbot.utils.AuthInterceptor
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    
    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: AuthInterceptor): OkHttpClient {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
        
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)