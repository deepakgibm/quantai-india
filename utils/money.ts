/**
 * Financial Math Utility
 * Uses Decimal.js for precise financial calculations.
 * 
 * JavaScript native floats have precision issues:
 *   0.1 + 0.2 = 0.30000000000000004
 * 
 * This utility ensures accurate P&L, price calculations, and display.
 */

import Decimal from 'decimal.js';

// Configure Decimal for Indian Rupee precision
Decimal.set({
    precision: 12,
    rounding: Decimal.ROUND_HALF_UP,
    toExpNeg: -9,
    toExpPos: 12,
});

/**
 * Money utility for financial calculations
 */
export const Money = {
    /**
     * Add two monetary values precisely
     * @example Money.add(100.05, 0.10) // 100.15 (not 100.15000000000001)
     */
    add: (a: number, b: number): number => {
        return new Decimal(a).plus(b).toNumber();
    },

    /**
     * Subtract: a - b
     * @example Money.subtract(100.00, 0.01) // 99.99
     */
    subtract: (a: number, b: number): number => {
        return new Decimal(a).minus(b).toNumber();
    },

    /**
     * Multiply (for quantity * price)
     * @example Money.multiply(299.99, 100) // 29999 (not 29999.000000000004)
     */
    multiply: (a: number, b: number): number => {
        return new Decimal(a).times(b).toNumber();
    },

    /**
     * Divide with precision
     * @example Money.divide(100, 3) // 33.333333333333
     */
    divide: (a: number, b: number): number => {
        if (b === 0) return 0;
        return new Decimal(a).dividedBy(b).toNumber();
    },

    /**
     * Calculate P&L (Profit & Loss)
     * @param currentPrice Current market price
     * @param entryPrice Entry/purchase price
     * @param quantity Number of shares
     * @returns Precise P&L value
     * @example Money.pnl(105.50, 100.00, 10) // 55.00
     */
    pnl: (currentPrice: number, entryPrice: number, quantity: number): number => {
        return new Decimal(currentPrice)
            .minus(entryPrice)
            .times(quantity)
            .toNumber();
    },

    /**
     * Calculate percentage change
     * @param newValue New value
     * @param oldValue Old value
     * @returns Percentage change as decimal (e.g., 0.05 for 5%)
     */
    percentChange: (newValue: number, oldValue: number): number => {
        if (oldValue === 0) return 0;
        return new Decimal(newValue)
            .minus(oldValue)
            .dividedBy(oldValue)
            .toNumber();
    },

    /**
     * Calculate percentage of a value
     * @example Money.percent(1000, 2.5) // 25 (2.5% of 1000)
     */
    percent: (value: number, percentage: number): number => {
        return new Decimal(value)
            .times(percentage)
            .dividedBy(100)
            .toNumber();
    },

    /**
     * Round to specified decimal places
     * @example Money.round(123.456789, 2) // 123.46
     */
    round: (value: number, decimals: number = 2): number => {
        return new Decimal(value).toDecimalPlaces(decimals).toNumber();
    },

    /**
     * Format for display with proper rounding
     * @example Money.format(1234.567, 2) // "1234.57"
     */
    format: (value: number, decimals: number = 2): string => {
        return new Decimal(value).toFixed(decimals);
    },

    /**
     * Format as Indian Rupee currency
     * @example Money.formatINR(123456.78) // "₹1,23,456.78"
     */
    formatINR: (value: number, decimals: number = 2): string => {
        const formatted = new Decimal(value).toFixed(decimals);
        const [whole, decimal] = formatted.split('.');

        // Indian number formatting (lakhs/crores system)
        const lastThree = whole.slice(-3);
        const otherNumbers = whole.slice(0, -3);
        const indianFormatted = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') +
            (otherNumbers ? ',' : '') + lastThree;

        return `₹${indianFormatted}${decimal ? '.' + decimal : ''}`;
    },

    /**
     * Compare two monetary values
     * @returns -1 if a < b, 0 if equal, 1 if a > b
     */
    compare: (a: number, b: number): number => {
        return new Decimal(a).comparedTo(b);
    },

    /**
     * Check if value is positive
     */
    isPositive: (value: number): boolean => {
        return new Decimal(value).isPositive() && new Decimal(value).gt(0);
    },

    /**
     * Check if value is negative
     */
    isNegative: (value: number): boolean => {
        return new Decimal(value).isNegative();
    },

    /**
     * Get absolute value
     */
    abs: (value: number): number => {
        return new Decimal(value).abs().toNumber();
    },

    /**
     * Clamp value between min and max
     */
    clamp: (value: number, min: number, max: number): number => {
        const d = new Decimal(value);
        if (d.lt(min)) return min;
        if (d.gt(max)) return max;
        return value;
    },

    /**
     * Calculate stop loss price
     * @param entryPrice Entry price
     * @param stopLossPercent Stop loss percentage (e.g., 2 for 2%)
     * @param isBuy True for buy orders (stop below entry), false for sell
     */
    stopLossPrice: (entryPrice: number, stopLossPercent: number, isBuy: boolean = true): number => {
        const factor = isBuy
            ? new Decimal(100).minus(stopLossPercent).dividedBy(100)
            : new Decimal(100).plus(stopLossPercent).dividedBy(100);
        return new Decimal(entryPrice).times(factor).toDecimalPlaces(2).toNumber();
    },

    /**
     * Calculate target price
     * @param entryPrice Entry price
     * @param targetPercent Target percentage (e.g., 5 for 5%)
     * @param isBuy True for buy orders, false for sell
     */
    targetPrice: (entryPrice: number, targetPercent: number, isBuy: boolean = true): number => {
        const factor = isBuy
            ? new Decimal(100).plus(targetPercent).dividedBy(100)
            : new Decimal(100).minus(targetPercent).dividedBy(100);
        return new Decimal(entryPrice).times(factor).toDecimalPlaces(2).toNumber();
    },

    /**
     * Calculate risk-reward ratio
     * @param entryPrice Entry price
     * @param targetPrice Target price
     * @param stopLoss Stop loss price
     * @returns Risk-reward ratio string (e.g., "1:2.5")
     */
    riskRewardRatio: (entryPrice: number, targetPrice: number, stopLoss: number): string => {
        const risk = new Decimal(entryPrice).minus(stopLoss).abs();
        const reward = new Decimal(targetPrice).minus(entryPrice).abs();

        if (risk.eq(0)) return "∞";

        const ratio = reward.dividedBy(risk);
        return `1:${ratio.toDecimalPlaces(1)}`;
    },
};

/**
 * Create a Decimal instance for complex calculations
 * @example 
 * const price = decimal(100.50);
 * const total = price.times(10).plus(50).toNumber();
 */
export const decimal = (value: number | string): Decimal => new Decimal(value);

export default Money;
