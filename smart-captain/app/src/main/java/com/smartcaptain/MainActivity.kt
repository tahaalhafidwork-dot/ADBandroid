package com.smartcaptain

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import android.view.Gravity

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val view = TextView(this).apply {
            text = "Smart Captain\nمساعد الكابتن\n\nالنسخة الأولية\n\nسيتم إضافة تحليل الرحلات والإعدادات في مراحل التنفيذ."
            textSize = 22f
            gravity = Gravity.CENTER
            setPadding(24, 24, 24, 24)
        }
        setContentView(view)
    }
}
