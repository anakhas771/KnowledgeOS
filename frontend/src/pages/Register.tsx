import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { authApi } from '../features/auth/api/authApi';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

export default function Register() {
  const [formData, setFormData] = useState({
    organization_name: '',
    organization_slug: '',
    email: '',
    username: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authApi.register(formData);
      navigate('/login');
    } catch (err: any) {
      if (err.response?.data) {
        setError(JSON.stringify(err.response.data));
      } else {
        setError('Registration failed.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-white p-8 shadow">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Create an Organization
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4 rounded-md shadow-sm">
            <Input name="organization_name" placeholder="Organization Name" required onChange={handleChange} />
            <Input name="organization_slug" placeholder="Organization Slug (e.g. acme-corp)" required onChange={handleChange} />
            <Input name="email" type="email" placeholder="Email Address" required onChange={handleChange} />
            <Input name="username" placeholder="Username" required onChange={handleChange} />
            <Input name="password" type="password" placeholder="Password" required onChange={handleChange} />
          </div>

          {error && <div className="text-sm text-red-500 break-words">{error}</div>}

          <div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Registering...' : 'Register'}
            </Button>
          </div>
          <div className="text-center text-sm">
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Already have an account? Sign in.
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
