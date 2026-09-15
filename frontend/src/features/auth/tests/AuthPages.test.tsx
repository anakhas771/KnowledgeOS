import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowserRouter } from 'react-router';
import Login from '../../../pages/Login';
import Register from '../../../pages/Register';

describe('Authentication Pages', () => {
  it('Login page renders correctly', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
    expect(screen.getByText('Sign in to KnowledgeOS')).toBeTruthy();
    expect(screen.getByPlaceholderText('Username')).toBeTruthy();
    expect(screen.getByPlaceholderText('Password')).toBeTruthy();
  });

  it('Register page renders correctly', () => {
    render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );
    expect(screen.getByText('Create an Organization')).toBeTruthy();
    expect(screen.getByPlaceholderText('Organization Name')).toBeTruthy();
    expect(screen.getByPlaceholderText('Email Address')).toBeTruthy();
  });
});
