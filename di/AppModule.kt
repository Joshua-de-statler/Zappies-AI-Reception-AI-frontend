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