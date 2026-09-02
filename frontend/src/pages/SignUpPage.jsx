import React from 'react'
import { SignUp } from '@clerk/react'

export default function SignUpPage() {
  return (
    <div className="flex justify-center items-center py-10 bg-slate-950">
      <SignUp 
        signInUrl="/sign-in" 
        redirectUrl="/dashboard"
        appearance={{
          variables: {
            colorPrimary: '#6366f1',
            colorBackground: '#1e293b',
            colorText: '#f8fafc',
            colorTextSecondary: '#94a3b8',
            colorInputBackground: '#0f172a',
            colorInputText: '#f8fafc',
            colorBorder: '#334155'
          },
          elements: {
            card: 'border border-slate-800 shadow-xl bg-slate-900',
            headerTitle: 'text-white font-extrabold',
            headerSubtitle: 'text-slate-400',
            socialButtonsBlockButton: 'border border-slate-850 hover:bg-slate-800 text-white font-semibold',
            formButtonPrimary: 'bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-indigo-500/20 shadow-md',
            footerActionLink: 'text-indigo-400 hover:text-indigo-300'
          }
        }}
      />
    </div>
  )
}
