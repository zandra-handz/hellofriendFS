import axios from 'axios';

import { ACCESS_TOKEN } from './constants';


const apiUrl = '/choreo-apis/hellofriend/hellofriend/rest-api-be2/v1.0'
const otherCode = 'VITE_API_URL= http://127.0.0.1:8000'

// access env variables
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : apiUrl, });

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem(ACCESS_TOKEN);
        console.log("Token:", token); // Add logging for token
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        console.error("Axios response error:", error);
        return Promise.reject(error);
    }
);

export default api;