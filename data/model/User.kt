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
