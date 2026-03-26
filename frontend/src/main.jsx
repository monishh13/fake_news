import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App.jsx'
import AdminLogin from './components/admin/AdminLogin.jsx'
import AdminDashboard from './components/admin/AdminDashboard.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <AuthProvider>
                    <Routes>
                        <Route path="/" element={<App />} />
                        <Route path="/admin/login" element={<AdminLogin />} />
                        <Route 
                            path="/admin/dashboard" 
                            element={
                                <ProtectedRoute>
                                    <AdminDashboard />
                                </ProtectedRoute>
                            } 
                        />
                    </Routes>
                </AuthProvider>
            </BrowserRouter>
        </QueryClientProvider>
    </React.StrictMode>,
)
