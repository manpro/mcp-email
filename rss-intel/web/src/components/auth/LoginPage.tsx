'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2, Rss, Smartphone, Globe, Mail } from 'lucide-react';

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      const success = await login(data.username, data.password);
      if (!success) {
        setError('Invalid username or password');
      }
    } catch (err) {
      setError('Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-blue-600 dark:bg-blue-500 rounded-2xl flex items-center justify-center mb-4">
            <Rss className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">RSS Intelligence</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Your personalized content hub with AI-powered insights
          </p>
        </div>

        {/* Features Preview */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="text-center p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50">
            <Smartphone className="h-6 w-6 text-blue-600 dark:text-blue-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">Mobile Ready</p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Responsive design</p>
          </div>
          <div className="text-center p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50">
            <Globe className="h-6 w-6 text-green-600 dark:text-green-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">Search & Filter</p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Advanced queries</p>
          </div>
          <div className="text-center p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50">
            <Mail className="h-6 w-6 text-purple-600 dark:text-purple-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">Email Client</p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Newsletter integration</p>
          </div>
          <div className="text-center p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50">
            <div className="h-6 w-6 bg-gradient-to-r from-orange-500 to-pink-500 rounded mx-auto mb-2 flex items-center justify-center">
              <span className="text-xs font-bold text-white">AI</span>
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">AI Analytics</p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Smart insights</p>
          </div>
        </div>

        {/* Login Form */}
        <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 shadow-xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center text-gray-900 dark:text-white">
              Sign In
            </CardTitle>
            <CardDescription className="text-center text-gray-600 dark:text-gray-400">
              Enter your credentials to access your dashboard
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
                  <AlertDescription className="text-red-800 dark:text-red-400">
                    {error}
                  </AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="username" className="text-gray-900 dark:text-white">Username</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  autoComplete="username"
                  {...form.register('username')}
                  className="bg-white/50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-600"
                  disabled={isLoading}
                />
                {form.formState.errors.username && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {form.formState.errors.username.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-gray-900 dark:text-white">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  {...form.register('password')}
                  className="bg-white/50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-600"
                  disabled={isLoading}
                />
                {form.formState.errors.password && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {form.formState.errors.password.message}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            {/* Demo Credentials */}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center mb-3">
                Demo Credentials:
              </p>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="font-medium text-gray-900 dark:text-white">owner</p>
                  <p className="text-gray-600 dark:text-gray-400">admin123</p>
                </div>
                <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="font-medium text-gray-900 dark:text-white">demo</p>
                  <p className="text-gray-600 dark:text-gray-400">demo123</p>
                </div>
                <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <p className="font-medium text-gray-900 dark:text-white">test</p>
                  <p className="text-gray-600 dark:text-gray-400">test123</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-sm text-gray-600 dark:text-gray-400">
          <p>Powered by AI-driven content intelligence</p>
        </div>
      </div>
    </div>
  );
};