// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Copyright (c) 2017 Rockchip Electronics Co. Ltd.
 * Author: Elaine <zhangqing@rock-chips.com>
 */

#include <linux/clk-provider.h>
#include <linux/io.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/syscore_ops.h>
#include <dt-bindings/clock/rk3128-cru.h>
#include "clk.h"

#define RK3128_GRF_SOC_STATUS0	0x14c

enum rk3128_plls {
	apll, dpll, cpll, gpll,
};

static struct rockchip_pll_rate_table rk3128_pll_rates[] = {
	/* _mhz, _refdiv, _fbdiv, _postdiv1, _postdiv2, _dsmpd, _frac */
	RK3036_PLL_RATE(1608000000, 1, 67, 1, 1, 1, 0),
	RK3036_PLL_RATE(1584000000, 1, 66, 1, 1, 1, 0),
	RK3036_PLL_RATE(1560000000, 1, 65, 1, 1, 1, 0),
	RK3036_PLL_RATE(1536000000, 1, 64, 1, 1, 1, 0),
	RK3036_PLL_RATE(1512000000, 1, 63, 1, 1, 1, 0),
	RK3036_PLL_RATE(1488000000, 1, 62, 1, 1, 1, 0),
	RK3036_PLL_RATE(1464000000, 1, 61, 1, 1, 1, 0),
	RK3036_PLL_RATE(1440000000, 1, 60, 1, 1, 1, 0),
	RK3036_PLL_RATE(1416000000, 1, 59, 1, 1, 1, 0),
	RK3036_PLL_RATE(1392000000, 1, 58, 1, 1, 1, 0),
	RK3036_PLL_RATE(1368000000, 1, 57, 1, 1, 1, 0),
	RK3036_PLL_RATE(1344000000, 1, 56, 1, 1, 1, 0),
	RK3036_PLL_RATE(1320000000, 1, 55, 1, 1, 1, 0),
	RK3036_PLL_RATE(1296000000, 1, 54, 1, 1, 1, 0),
	RK3036_PLL_RATE(1272000000, 1, 53, 1, 1, 1, 0),
	RK3036_PLL_RATE(1248000000, 1, 52, 1, 1, 1, 0),
	RK3036_PLL_RATE(1200000000, 1, 50, 1, 1, 1, 0),
	RK3036_PLL_RATE(1188000000, 2, 99, 1, 1, 1, 0),
	RK3036_PLL_RATE(1104000000, 1, 46, 1, 1, 1, 0),
	RK3036_PLL_RATE(1100000000, 12, 550, 1, 1, 1, 0),
	RK3036_PLL_RATE(1008000000, 1, 84, 2, 1, 1, 0),
	RK3036_PLL_RATE(1000000000, 6, 500, 2, 1, 1, 0),
	RK3036_PLL_RATE(984000000, 1, 82, 2, 1, 1, 0),
	RK3036_PLL_RATE(960000000, 1, 80, 2, 1, 1, 0),
	RK3036_PLL_RATE(936000000, 1, 78, 2, 1, 1, 0),
	RK3036_PLL_RATE(912000000, 1, 76, 2, 1, 1, 0),
	RK3036_PLL_RATE(900000000, 4, 300, 2, 1, 1, 0),
	RK3036_PLL_RATE(888000000, 1, 74, 2, 1, 1, 0),
	RK3036_PLL_RATE(864000000, 1, 72, 2, 1, 1, 0),
	RK3036_PLL_RATE(840000000, 1, 70, 2, 1, 1, 0),
	RK3036_PLL_RATE(816000000, 1, 68, 2, 1, 1, 0),
	RK3036_PLL_RATE(800000000, 6, 400, 2, 1, 1, 0),
	RK3036_PLL_RATE(700000000, 6, 350, 2, 1, 1, 0),
	RK3036_PLL_RATE(696000000, 1, 58, 2, 1, 1, 0),
	RK3036_PLL_RATE(600000000, 1, 75, 3, 1, 1, 0),
	RK3036_PLL_RATE(594000000, 2, 99, 2, 1, 1, 0),
	RK3036_PLL_RATE(504000000, 1, 63, 3, 1, 1, 0),
	RK3036_PLL_RATE(500000000, 6, 250, 2, 1, 1, 0),
	RK3036_PLL_RATE(408000000, 1, 68, 2, 2, 1, 0),
	RK3036_PLL_RATE(312000000, 1, 52, 2, 2, 1, 0),
	RK3036_PLL_RATE(216000000, 1, 72, 4, 2, 1, 0),
	RK3036_PLL_RATE(96000000, 1, 64, 4, 4, 1, 0),
	{ /* sentinel */ },
};

#define RK3128_DIV_CPU_MASK		0x1f
#define RK3128_DIV_CPU_SHIFT		8

#define RK3128_DIV_PERI_MASK		0xf
#define RK3128_DIV_PERI_SHIFT		0
#define RK3128_DIV_ACLK_MASK		0x7
#define RK3128_DIV_ACLK_SHIFT		4
#define RK3128_DIV_HCLK_MASK		0x3
#define RK3128_DIV_HCLK_SHIFT		8
#define RK3128_DIV_PCLK_MASK		0x7
#define RK3128_DIV_PCLK_SHIFT		12

#define RK3128_CLKSEL1(_core_aclk_div, _pclk_dbg_div)			\
{									\
	.reg = RK2928_CLKSEL_CON(1),					\
	.val = HIWORD_UPDATE(_pclk_dbg_div, RK3128_DIV_PERI_MASK,	\
			     RK3128_DIV_PERI_SHIFT) |			\
	       HIWORD_UPDATE(_core_aclk_div, RK3128_DIV_ACLK_MASK,	\
			     RK3128_DIV_ACLK_SHIFT),			\
}

#define RK3128_CPUCLK_RATE(_prate, _core_aclk_div, _pclk_dbg_div)	\
{									\
	.prate = _prate,						\
	.divs = {							\
		RK3128_CLKSEL1(_core_aclk_div, _pclk_dbg_div),		\
	},								\
}

static struct rockchip_cpuclk_rate_table rk3128_cpuclk_rates[] __initdata = {
	RK3128_CPUCLK_RATE(1800000000, 1, 7),
	RK3128_CPUCLK_RATE(1704000000, 1, 7),
	RK3128_CPUCLK_RATE(1608000000, 1, 7),
	RK3128_CPUCLK_RATE(1512000000, 1, 7),
	RK3128_CPUCLK_RATE(1488000000, 1, 5),
	RK3128_CPUCLK_RATE(1416000000, 1, 5),
	RK3128_CPUCLK_RATE(1392000000, 1, 5),
	RK3128_CPUCLK_RATE(1296000000, 1, 5),
	RK3128_CPUCLK_RATE(1200000000, 1, 5),
	RK3128_CPUCLK_RATE(1104000000, 1, 5),
	RK3128_CPUCLK_RATE(1008000000, 1, 5),
	RK3128_CPUCLK_RATE(912000000, 1, 5),
	RK3128_CPUCLK_RATE(816000000, 1, 3),
	RK3128_CPUCLK_RATE(696000000, 1, 3),
	RK3128_CPUC