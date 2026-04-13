import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import workflowReducer from './workflowSlice';
import uiReducer from './uiSlice';
import sessionReducer from './sessionSlice';

export const store = configureStore({
  reducer: {
    workflows: workflowReducer,
    ui: uiReducer,
    sessions: sessionReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false, // allow Date objects in state
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
